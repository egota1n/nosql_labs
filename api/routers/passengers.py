from fastapi import APIRouter, HTTPException, Query, Depends
from models.pydantic_models import (
    Passenger, PassengerCreate, PassengerUpdate, 
    PassengerWithTickets, CountryStats
)
from db.mongo import get_mongo_collection
from db.cassandra import get_cassandra_session
from typing import List
import uuid
from datetime import datetime

router = APIRouter(
    tags=["Passengers"],
    prefix="/passengers",
    responses={404: {"description": "Not found"}}
)

def get_passengers_collection():
    return get_mongo_collection("passengers")

def get_cassandra():
    return get_cassandra_session()

# POST: /api/passengers – Create Passenger
@router.post("/passengers", response_model=Passenger, status_code=201)
async def create_passenger(passenger: PassengerCreate):
    collection = get_passengers_collection()
    passenger_id = f"pas_{uuid.uuid4().hex[:8]}"
    passenger_data = {
        "passenger_id": passenger_id,
        **passenger.dict(),
        "created_at": datetime.utcnow()
    }
    
    result = await collection.insert_one(passenger_data)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create passenger")
    
    return {**passenger_data, "tickets": []}

# GET: /api/passengers – Get Passengers
@router.get("/passengers", response_model=List[Passenger])
async def get_passengers(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    collection = get_passengers_collection()
    passengers = []
    async for doc in collection.find().skip(offset).limit(limit):
        passengers.append(Passenger(**doc))
    return passengers

# GET: /api/passengers/{passenger_id} – Get Passenger
@router.get("/passengers/{passenger_id}", response_model=PassengerWithTickets)
async def get_passenger(passenger_id: str):
    collection = get_passengers_collection()
    passenger = await collection.find_one({"passenger_id": passenger_id})
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
    cassandra = get_cassandra()
    rows = cassandra.execute(
        "SELECT * FROM tickets WHERE passenger_id = %s",
        [passenger_id]
    )
    
    tickets = []
    for row in rows:
        tickets.append({
            "ticket_id": row.ticket_id,
            "flight_id": row.flight_id,
            "seat": row.seat,
            "class_place": row.class_place,
            "price": float(row.price),
            "booking_date": row.booking_date
        })
    
    return {**passenger, "tickets": tickets}

# PUT: /api/passengers/{passenger_id} – Update Passenger
@router.put("/passengers/{passenger_id}", response_model=Passenger)
async def update_passenger(
    passenger_id: str, 
    update_data: PassengerUpdate
):
    collection = get_passengers_collection()
    update_fields = {k: v for k, v in update_data.dict().items() if v is not None}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No data to update")
    
    result = await collection.update_one(
        {"passenger_id": passenger_id},
        {"$set": {**update_fields, "updated_at": datetime.utcnow()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Passenger not found or no changes")
    
    updated_passenger = await collection.find_one({"passenger_id": passenger_id})
    return Passenger(**updated_passenger)

# DELETE: /api/passengers/{passenger_id} – Delete Passenger
@router.delete("/passengers/{passenger_id}", status_code=204)
async def delete_passenger(passenger_id: str):
    collection = get_passengers_collection()
    result = await collection.delete_one({"passenger_id": passenger_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
    cassandra = get_cassandra()
    cassandra.execute(
        "DELETE FROM tickets WHERE passenger_id = %s",
        [passenger_id]
    )
    
    return

# GET: /api/passengers/stats/country – Get Passengers By Country
@router.get("/passengers/stats/country", response_model=List[CountryStats])
async def get_passengers_by_country():
    collection = get_passengers_collection()
    pipeline = [
        {"$group": {"_id": "$nationality", "count": {"$sum": 1}}},
        {"$project": {"country": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"count": -1}}
    ]
    
    result = []
    async for doc in collection.aggregate(pipeline):
        result.append(CountryStats(**doc))
    return result

# GET: /api/passengers/{passenger_id}/total_spent – Get Total Spent
@router.get("/passengers/{passenger_id}/total_spent")
async def get_total_spent(passenger_id: str):
    cassandra = get_cassandra()
    
    mongo_collection = get_mongo_collection("passengers")
    passenger = await mongo_collection.find_one({"passenger_id": passenger_id})
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
    try:
        rows = cassandra.execute(
            "SELECT price FROM tickets WHERE passenger_id = %s",
            [passenger_id]
        )
    except Exception as e:
        logger.error(f"Cassandra query failed: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    
    total = sum(float(row.price) for row in rows)
    
    return {
        "passenger_id": passenger_id,
        "total_spent": round(total, 2),
        "currency": "USD"
    }

# GET: /api/passengers/{passenger_id}/travel_history – Get Travel History
@router.get("/passengers/{passenger_id}/travel_history")
async def get_travel_history(passenger_id: str):
    from db.neo4j import get_neo4j_driver
    
    driver = get_neo4j_driver()
    query = """
    MATCH (p:Passenger {passenger_id: $passenger_id})-[:BOOKED_FLIGHT]->(f:Flight)
    OPTIONAL MATCH (f)-[:DEPARTS_FROM]->(dep:Airport)
    OPTIONAL MATCH (f)-[:ARRIVES_AT]->(arr:Airport)
    RETURN f.flight_id AS flight_id,
           f.departure_time AS departure_time,
           f.arrival_time AS arrival_time,
           dep.code AS departure_airport,
           arr.code AS arrival_airport
    ORDER BY f.departure_time DESC
    """
    
    history = []
    with driver.session() as session:
        result = session.run(query, passenger_id=passenger_id)
        for record in result:
            dep_time = record["departure_time"]
            arr_time = record["arrival_time"]
            
            formatted_departure = (
                dep_time.strftime("%Y-%m-%d %H:%M:%S")
                if dep_time else None
            )
            
            formatted_arrival = (
                arr_time.strftime("%Y-%m-%d %H:%M:%S")
                if arr_time else None
            )
            
            history.append({
                "flight_id": record["flight_id"],
                "departure_time": formatted_departure,
                "arrival_time": formatted_arrival,
                "departure_airport": record["departure_airport"],
                "arrival_airport": record["arrival_airport"]
            })
    
    return {"passenger_id": passenger_id, "travel_history": history}
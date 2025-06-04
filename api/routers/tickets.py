from fastapi import APIRouter, HTTPException, Query, Depends
from models.pydantic_models import Ticket, TicketCreate, TicketUpdate, TicketStats, TicketWithDetails
from db.cassandra import get_cassandra_session
from db.mongo import get_mongo_collection
from db.neo4j import get_neo4j_driver
from datetime import datetime
import uuid
import logging
from typing import List

router = APIRouter(
    tags=["Tickets"],
    prefix="/tickets",
    responses={404: {"description": "Not found"}}
)

logger = logging.getLogger("tickets")

def get_cassandra():
    return get_cassandra_session()

# POST: /api/tickets – Create Ticket
@router.post("", response_model=Ticket, status_code=201)
async def create_ticket(ticket: TicketCreate):
    cassandra = get_cassandra()
    ticket_id = f"tkt_{uuid.uuid4().hex[:6]}"
    booking_date = datetime.utcnow()
    
    mongo_collection = get_mongo_collection("passengers")
    passenger = await mongo_collection.find_one({"passenger_id": ticket.passenger_id})
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
    query = """
    INSERT INTO tickets (
        ticket_id, passenger_id, flight_id, 
        seat, class, price, booking_date
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        cassandra.execute(query, (
            ticket_id, ticket.passenger_id, ticket.flight_id,
            ticket.seat, ticket.class_place, ticket.price, booking_date
        ))
    except Exception as e:
        logger.error(f"Failed to create ticket: {e}")
        raise HTTPException(status_code=500, detail="Failed to create ticket")
    
    return {
        "ticket_id": ticket_id,
        "passenger_id": ticket.passenger_id,
        "flight_id": ticket.flight_id,
        "seat": ticket.seat,
        "class_place": ticket.class_place,
        "price": ticket.price,
        "booking_date": booking_date
    }

# GET: /api/tickets – Get Tickets
@router.get("", response_model=List[Ticket])
async def get_tickets(
    passenger_id: str = Query(None, description="Фильтр по пассажиру"),
    flight_id: str = Query(None, description="Фильтр по рейсу"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    cassandra = get_cassandra()
    query = "SELECT * FROM tickets"
    params = []
    
    if passenger_id or flight_id:
        query += " WHERE "
        conditions = []
        if passenger_id:
            conditions.append("passenger_id = %s")
            params.append(passenger_id)
        if flight_id:
            conditions.append("flight_id = %s")
            params.append(flight_id)
        query += " AND ".join(conditions)
    
    query += " LIMIT %s"
    params.append(limit)
    
    try:
        rows = cassandra.execute(query, params)
        tickets = []
        for row in rows:
            tickets.append({
                "ticket_id": row.ticket_id,
                "passenger_id": row.passenger_id,
                "flight_id": row.flight_id,
                "seat": row.seat,
                "class_place": row.class_place,
                "price": float(row.price),
                "booking_date": row.booking_date
            })
        return tickets
    except Exception as e:
        logger.error(f"Failed to get tickets: {e}")
        raise HTTPException(status_code=500, detail="Database error")

# GET: /api/tickets/{ticket_id} – Get Ticket
@router.get("/{ticket_id}", response_model=TicketWithDetails)
async def get_ticket(ticket_id: str):
    cassandra = get_cassandra()
    query = "SELECT * FROM tickets WHERE ticket_id = %s"
    
    try:
        row = cassandra.execute(query, [ticket_id]).one()
        if not row:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        ticket = {
            "ticket_id": row.ticket_id,
            "passenger_id": row.passenger_id,
            "flight_id": row.flight_id,
            "seat": row.seat,
            "class_place": row.class_place,
            "price": float(row.price),
            "booking_date": row.booking_date
        }
        
        mongo_collection = get_mongo_collection("passengers")
        passenger = await mongo_collection.find_one({"passenger_id": ticket["passenger_id"]})
        ticket["passenger_name"] = passenger["full_name"] if passenger else "Unknown"
        
        driver = get_neo4j_driver()
        flight_info = {}
        with driver.session() as session:
            result = session.run("""
                MATCH (f:Flight {flight_id: $flight_id})-[:DEPARTS_FROM]->(dep:Airport)
                MATCH (f)-[:ARRIVES_AT]->(arr:Airport)
                RETURN dep.code AS departure, arr.code AS arrival
            """, flight_id=ticket["flight_id"])
            
            record = result.single()
            if record:
                flight_info = {
                    "departure_airport": record["departure"],
                    "arrival_airport": record["arrival"]
                }
        
        ticket["flight_route"] = f"{flight_info.get('departure_airport', '?')} → {flight_info.get('arrival_airport', '?')}"
        
        return ticket
        
    except Exception as e:
        logger.error(f"Failed to get ticket: {e}")
        raise HTTPException(status_code=500, detail="Database error")

# PUT: /api/tickets/{ticket_id} – Update Ticket
@router.put("/{ticket_id}", response_model=Ticket)
async def update_ticket(ticket_id: str, update_data: TicketUpdate):
    cassandra = get_cassandra()
    
    existing = cassandra.execute(
        "SELECT * FROM tickets WHERE ticket_id = %s", 
        [ticket_id]
    ).one()
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    set_clauses = []
    params = []
    
    if update_data.seat is not None:
        set_clauses.append("seat = %s")
        params.append(update_data.seat)
    if update_data.class_place is not None:
        set_clauses.append("class_place = %s")
        params.append(update_data.class_place)
    if update_data.price is not None:
        set_clauses.append("price = %s")
        params.append(update_data.price)
    
    if not set_clauses:
        raise HTTPException(status_code=400, detail="No data to update")
    
    query = f"UPDATE tickets SET {', '.join(set_clauses)} WHERE ticket_id = %s"
    params.append(ticket_id)
    
    try:
        cassandra.execute(query, params)
        updated = cassandra.execute(
            "SELECT * FROM tickets WHERE ticket_id = %s", 
            [ticket_id]
        ).one()
        return {
            "ticket_id": updated.ticket_id,
            "passenger_id": updated.passenger_id,
            "flight_id": updated.flight_id,
            "seat": updated.seat,
            "class_place": updated.class_place,
            "price": float(updated.price),
            "booking_date": updated.booking_date
        }
    except Exception as e:
        logger.error(f"Failed to update ticket: {e}")
        raise HTTPException(status_code=500, detail="Database error")

# DELETE: /api/tickets/{ticket_id} – Delete Ticket
@router.delete("/{ticket_id}", status_code=204)
async def delete_ticket(ticket_id: str):
    cassandra = get_cassandra()
    
    existing = cassandra.execute(
        "SELECT * FROM tickets WHERE ticket_id = %s", 
        [ticket_id]
    ).one()
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    try:
        cassandra.execute(
            "DELETE FROM baggage WHERE ticket_id = %s",
            [ticket_id]
        )
    except Exception as e:
        logger.warning(f"Failed to delete related baggage: {e}")
    
    try:
        cassandra.execute(
            "DELETE FROM tickets WHERE ticket_id = %s",
            [ticket_id]
        )
        return
    except Exception as e:
        logger.error(f"Failed to delete ticket: {e}")
        raise HTTPException(status_code=500, detail="Database error")
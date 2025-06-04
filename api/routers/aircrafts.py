from fastapi import APIRouter, HTTPException, Query, Depends, Header
from models.pydantic_models import (
    Aircraft, AircraftCreate, AircraftUpdate, 
    ManufacturerStats, AircraftFlights
)
from db.mongo import get_mongo_collection
from datetime import datetime
from typing import List
import uuid

router = APIRouter(
    tags=["Aircrafts"],
    prefix="/aircrafts",
    responses={404: {"description": "Not found"}}
)

def get_aircrafts_collection():
    return get_mongo_collection("aircrafts")

# POST: /api/aircrafts – Create Aircraft
@router.post("", response_model=Aircraft, status_code=201)
async def create_aircraft(aircraft: AircraftCreate):
    collection = get_aircrafts_collection()
    reg_number = f"REG-{uuid.uuid4().hex[:6]}"
    aircraft_data = {
        "reg_number": reg_number,
        **aircraft.dict(),
        "last_maintenance": datetime.utcnow()
    }
    
    result = await collection.insert_one(aircraft_data)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create aircraft")
    
    return aircraft_data

# GET: /api/aircrafts – Get Aircrafts
@router.get("", response_model=List[Aircraft])
async def get_aircrafts(
    status: str = Query(None, description="Фильтр по статусу"),
    min_capacity: int = Query(0, description="Минимальная вместимость"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    collection = get_aircrafts_collection()
    query = {}
    
    if status:
        query["status"] = status
    if min_capacity > 0:
        query["capacity"] = {"$gte": min_capacity}
    
    aircrafts = []
    async for doc in collection.find(query).skip(offset).limit(limit):
        aircrafts.append(Aircraft(**doc))
    return aircrafts

# GET: /api/aircrafts/{reg_number} – Get Aircraft
@router.get("/{reg_number}", response_model=Aircraft)
async def get_aircraft(reg_number: str):
    collection = get_aircrafts_collection()
    aircraft = await collection.find_one({"reg_number": reg_number})
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    return aircraft

# PUT: /api/aircrafts/{reg_number} – Update Aircraft
@router.put("/{reg_number}", response_model=Aircraft)
async def update_aircraft(
    reg_number: str, 
    update_data: AircraftUpdate
):
    collection = get_aircrafts_collection()
    update_fields = {k: v for k, v in update_data.dict().items() if v is not None}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No data to update")
    
    if "status" in update_fields and update_fields["status"] == "maintenance":
        update_fields["last_maintenance"] = datetime.utcnow()
    
    result = await collection.update_one(
        {"reg_number": reg_number},
        {"$set": update_fields}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Aircraft not found or no changes")
    
    updated_aircraft = await collection.find_one({"reg_number": reg_number})
    return updated_aircraft

# DELETE: /api/aircrafts/{reg_number} – Delete Aircraft
@router.delete("/{reg_number}", status_code=204)
async def delete_aircraft(reg_number: str):
    collection = get_aircrafts_collection()
    result = await collection.delete_one({"reg_number": reg_number})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    
    return
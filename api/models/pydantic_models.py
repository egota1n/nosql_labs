from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# Aircraft
class Aircraft(BaseModel):
    reg_number: str
    model: str
    manufacturer: str
    capacity: int
    last_maintenance: datetime
    status: str

class AircraftCreate(BaseModel):
    model: str
    manufacturer: str
    capacity: int
    status: str

class AircraftUpdate(BaseModel):
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[str] = None
    last_maintenance: Optional[datetime] = None

class ManufacturerStats(BaseModel):
    manufacturer: str
    count: int
    total_capacity: int

class AircraftFlights(BaseModel):
    flight_id: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime

# Ticket
class Ticket(BaseModel):
    ticket_id: str
    flight_id: str
    seat: str
    class_place: str
    price: float
    booking_date: datetime

class TicketCreate(BaseModel):
    passenger_id: str
    flight_id: str
    seat: str
    class_place: str
    price: float

class TicketUpdate(BaseModel):
    seat: Optional[str] = None
    class_place: Optional[str] = None
    price: Optional[float] = None

class TicketStats(BaseModel):
    class_place: str
    count: int
    total_revenue: float

class TicketWithDetails(Ticket):
    passenger_name: str
    flight_route: str

# Passenger
class Contact(BaseModel):
    email: EmailStr
    phone: str

class Passenger(BaseModel):
    passenger_id: str
    full_name: str
    passport: str
    nationality: str
    contact: Contact
    tickets: List[Ticket]

class PassengerCreate(BaseModel):
    full_name: str
    passport: str
    nationality: str
    contact: Contact

class PassengerUpdate(BaseModel):
    full_name: Optional[str] = None
    passport: Optional[str] = None
    nationality: Optional[str] = None
    contact: Optional[Contact] = None

class PassengerWithTickets(Passenger):
    tickets: List[Ticket] = []


# Other

class CountryStats(BaseModel):
    country: str
    count: int

class Flight(BaseModel):
    flight_id: str
    airline: dict
    aircraft: str
    status: str
    departure: dict
    arrival: dict
    passengers: List[str]

class Airport(BaseModel):
    code: str
    name: str
    city: str
    country: str
    runways: int

class Baggage(BaseModel):
    baggage_id: str
    last_updated: datetime
    status: str
    ticket_id: str
    weight: float
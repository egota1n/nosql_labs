import pymongo
from faker import Faker
from datetime import datetime, timedelta
import random
import uuid

fake = Faker()
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["airport_db"]

db.flights.drop()
db.passengers.drop()
db.aircrafts.drop()
db.airports.drop()

aircraft_reg_numbers = []
airport_codes = []
passenger_ids = []

def generate_airports(num=20):
    airports = []
    major_airports = ["SVO", "JFK", "LAX", "LED", "IST", "DXB", "HND", "LHR", "CDG", "FRA"]
    
    for code in major_airports:
        airports.append({
            "code": code,
            "name": fake.company() + " International Airport",
            "city": fake.city(),
            "country": fake.country(),
            "runways": random.randint(2, 5)
        })
        airport_codes.append(code)
    
    for _ in range(num - len(major_airports)):
        code = fake.unique.bothify(text="???", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        airports.append({
            "code": code,
            "name": fake.city() + " Airport",
            "city": fake.city(),
            "country": fake.country(),
            "runways": random.randint(1, 3)
        })
        airport_codes.append(code)
    
    db.airports.insert_many(airports)

def generate_aircrafts(num=50):
    aircraft_models = [
        "Boeing 737-800", "Airbus A320", "Boeing 787", "Airbus A350",
        "Embraer E190", "Boeing 777", "Airbus A380", "Bombardier CRJ900"
    ]
    
    aircrafts = []
    for _ in range(num):
        reg_number = fake.unique.bothify(text="??-#####", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        aircrafts.append({
            "reg_number": reg_number,
            "model": random.choice(aircraft_models),
            "manufacturer": "Boeing" if "Boeing" in aircraft_models else "Airbus",
            "capacity": random.randint(100, 400),
            "last_maintenance": datetime.now() - timedelta(days=random.randint(1, 365)),
            "status": random.choice(["active", "maintenance", "storage"])
        })
        aircraft_reg_numbers.append(reg_number)
    
    db.aircrafts.insert_many(aircrafts)

def generate_passengers(num=20_000):
    passengers = []
    for _ in range(num):
        passenger_id = f"pas_{uuid.uuid4().hex[:8]}"
        passengers.append({
            "passenger_id": passenger_id,
            "full_name": fake.name(),
            "passport": fake.unique.bothify(text="#########"),
            "nationality": fake.country_code(),
            "contact": {
                "email": fake.email(),
                "phone": fake.phone_number()
            },
            "tickets": []
        })
        passenger_ids.append(passenger_id)
    
    for i in range(0, len(passengers), 10000):
        db.passengers.insert_many(passengers[i:i+10000])

def generate_flights_and_tickets(num_flights=100, tickets_per_flight=100):
    airlines = [
        {"code": "SU", "name": "Aeroflot"},
        {"code": "DL", "name": "Delta Airlines"},
        {"code": "AA", "name": "American Airlines"},
        {"code": "TK", "name": "Turkish Airlines"}
    ]
    
    flight_statuses = ["scheduled", "boarding", "departed", "delayed", "canceled"]
    
    for _ in range(num_flights):
        departure_airport = random.choice(airport_codes)
        arrival_airport = random.choice([c for c in airport_codes if c != departure_airport])
        
        flight_id = f"{random.choice(airlines)['code']}-{fake.unique.random_int(min=1000, max=9999)}"
        departure_time = datetime.now() - timedelta(days=random.randint(1, 365))
        
        flight_data = {
            "flight_id": flight_id,
            "airline": random.choice(airlines),
            "aircraft": random.choice(aircraft_reg_numbers),
            "status": random.choice(flight_statuses),
            "departure": {
                "airport": departure_airport,
                "time": departure_time,
                "gate": fake.bothify(text="?##", letters="ABCDE")
            },
            "arrival": {
                "airport": arrival_airport,
                "time": departure_time + timedelta(hours=random.randint(1, 12))
            },
            "passengers": []
        }
        
        num_tickets = random.randint(int(tickets_per_flight*0.5), int(tickets_per_flight*1.5))
        flight_passengers = random.sample(passenger_ids, min(num_tickets, len(passenger_ids)))
        
        for passenger_id in flight_passengers:
            ticket_id = f"tkt_{uuid.uuid4().hex[:6]}"
            
            db.passengers.update_one(
                {"passenger_id": passenger_id},
                {"$push": {"tickets": {
                    "ticket_id": ticket_id,
                    "flight_id": flight_id,
                    "seat": f"{random.randint(1, 40)}{random.choice('ABCDEF')}",
                    "class_place": random.choice(["economy", "business", "first"]),
                    "price": round(random.uniform(50, 2000), 2),
                    "booking_date": datetime.now() - timedelta(days=random.randint(1, 365))
                }}}
            )
            
            flight_data["passengers"].append(passenger_id)
        
        db.flights.insert_one(flight_data)

if __name__ == "__main__":
    generate_airports()
    print(f"Генерация аэропортов – {db.airports.count_documents({})}")
    
    generate_aircrafts()
    print(f"Генерация самолетов – {db.aircrafts.count_documents({})}")
    
    generate_passengers()
    print(f"Генерация пассажиров – {db.passengers.count_documents({})}")
    
    generate_flights_and_tickets()
    print(f"Генерация рейсов – {db.flights.count_documents({})}")
    
    db.flights.create_index("flight_id", unique=True)
    db.flights.create_index("status")
    db.flights.create_index("departure.airport")
    db.flights.create_index("departure.time")
    db.passengers.create_index("passenger_id", unique=True)
    db.passengers.create_index("passport", unique=True)
    db.aircrafts.create_index("reg_number", unique=True)
    db.airports.create_index("code", unique=True)
    
    print("Созданы индексы")
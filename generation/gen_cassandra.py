from cassandra.cluster import Cluster
from cassandra.query import BatchStatement, SimpleStatement
from cassandra import ConsistencyLevel
from pymongo import MongoClient
from datetime import datetime, timedelta
import random
import uuid
import time

mongo_client = MongoClient('mongodb://localhost:27017/')
mongo_db = mongo_client['airport_db']

cluster = Cluster(['localhost'])
session = cluster.connect()

session.execute("""
CREATE KEYSPACE IF NOT EXISTS airport 
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
""")

session.set_keyspace('airport')

session.execute("DROP TABLE IF EXISTS tickets")
session.execute("DROP TABLE IF EXISTS baggage")
session.execute("DROP TABLE IF EXISTS flight_status")

session.execute("""
CREATE TABLE tickets (
    ticket_id TEXT PRIMARY KEY,
    passenger_id TEXT,
    flight_id TEXT,
    seat TEXT,
    class_place TEXT,
    price DECIMAL,
    booking_date TIMESTAMP
)
""")

session.execute("""
CREATE TABLE baggage (
    baggage_id UUID PRIMARY KEY,
    ticket_id TEXT,
    weight FLOAT,
    status TEXT,
    last_updated TIMESTAMP
)
""")

session.execute("""
CREATE TABLE flight_status (
    flight_id TEXT PRIMARY KEY,
    status TEXT,
    last_update TIMESTAMP,
    departure_airport TEXT,
    arrival_airport TEXT
)
""")

insert_ticket = session.prepare("""
INSERT INTO tickets (ticket_id, passenger_id, flight_id, seat, class_place, price, booking_date)
VALUES (?, ?, ?, ?, ?, ?, ?)
""")

insert_baggage = session.prepare("""
INSERT INTO baggage (baggage_id, ticket_id, weight, status, last_updated)
VALUES (?, ?, ?, ?, ?)
""")

insert_status = session.prepare("""
INSERT INTO flight_status (flight_id, status, last_update, departure_airport, arrival_airport)
VALUES (?, ?, ?, ?, ?)
""")

ticket_counter = 0
baggage_counter = 0

ticket_batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)
baggage_batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)
batch_size = 50

for passenger in mongo_db.passengers.find():
    for ticket in passenger.get('tickets', []):
        try:
            ticket_batch.add(insert_ticket, (
                ticket['ticket_id'],
                passenger['passenger_id'],
                ticket['flight_id'],
                ticket['seat'],
                ticket['class_place'],
                float(ticket['price']),
                ticket['booking_date']
            ))
            
            for _ in range(random.randint(1, 2)):
                baggage_batch.add(insert_baggage, (
                    uuid.uuid4(),
                    ticket['ticket_id'],
                    round(random.uniform(5, 32), 1),
                    random.choice(['checked_in', 'in_transit', 'loaded', 'delivered']),
                    datetime.now()
                ))
                baggage_counter += 1
            
            ticket_counter += 1
            
            if ticket_counter % batch_size == 0:
                session.execute(ticket_batch)
                session.execute(baggage_batch)
                ticket_batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)
                baggage_batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)
                
        except Exception as e:
            print(f"Ошибка при обработке билета {ticket['ticket_id']}: {str(e)}")

if ticket_batch:
    session.execute(ticket_batch)
if baggage_batch:
    session.execute(baggage_batch)

status_batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)
status_counter = 0

for flight in mongo_db.flights.find():
    try:
        status_batch.add(insert_status, (
            flight['flight_id'],
            flight['status'],
            datetime.now(),
            flight['departure']['airport'],
            flight['arrival']['airport']
        ))
        status_counter += 1
        
        if status_counter % batch_size == 0:
            session.execute(status_batch)
            status_batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)
            print(f"Обработано статусов: {status_counter}")
            
    except Exception as e:
        print(f"Ошибка при обработке рейса {flight['flight_id']}: {str(e)}")

if status_batch:
    session.execute(status_batch)

session.execute("CREATE INDEX ON tickets(passenger_id)")
session.execute("CREATE INDEX ON tickets(flight_id)")
session.execute("CREATE INDEX ON baggage(ticket_id)")
session.execute("CREATE INDEX ON flight_status(departure_airport)")
session.execute("CREATE INDEX ON flight_status(arrival_airport)")

print("Созданы индексы")

cluster.shutdown()
mongo_client.close()  
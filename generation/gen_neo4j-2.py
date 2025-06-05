from pymongo import MongoClient
from neo4j import GraphDatabase
from datetime import datetime
import os
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mongo_to_neo4j")

class MongoNeo4jMigrator:
    def __init__(self):
        self.mongo_client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
        self.mongo_db = self.mongo_client["airport_db"]
        
        self.neo4j_driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "test1234")
            )
        )
    
    def clean_neo4j_database(self):
        with self.neo4j_driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            
            constraints = session.run("SHOW CONSTRAINTS").data()
            for constraint in constraints:
                session.run(f"DROP CONSTRAINT {constraint['name']} IF EXISTS")
            
            indexes = session.run("SHOW INDEXES").data()
            for index in indexes:
                if not index['name'].startswith('token'):
                    session.run(f"DROP INDEX {index['name']} IF EXISTS")
            
            logger.info("Neo4j database cleaned (nodes, relationships, constraints and indexes removed)")
    
    def create_neo4j_constraints(self):
        with self.neo4j_driver.session() as session:
            create_constraint_queries = [
                "CREATE CONSTRAINT FOR (a:Airport) REQUIRE a.code IS UNIQUE",
                "CREATE CONSTRAINT FOR (p:Passenger) REQUIRE p.passenger_id IS UNIQUE",
                "CREATE CONSTRAINT FOR (f:Flight) REQUIRE f.flight_id IS UNIQUE"
            ]
            
            for query in create_constraint_queries:
                try:
                    session.run(query)
                    logger.info(f"Created constraint: {query}")
                except Exception as e:
                    logger.error(f"Failed to create constraint: {e}")
            
            create_index_queries = [
                "CREATE INDEX FOR (f:Flight) ON (f.departure_time)",
                "CREATE INDEX FOR (f:Flight) ON (f.arrival_time)"
            ]
            
            for query in create_index_queries:
                try:
                    session.run(query)
                    logger.info(f"Created index: {query}")
                except Exception as e:
                    logger.error(f"Failed to create index: {e}")

    def migrate_airports(self):
        airports = self.mongo_db.airports.find()
        count = 0
        with self.neo4j_driver.session() as session:
            for airport in airports:
                airport_data = {
                    "code": airport.get("code"),
                    "name": airport.get("name"),
                    "city": airport.get("city"),
                    "country": airport.get("country"),
                    "runways": airport.get("runways")
                }
                session.run("""
                    MERGE (a:Airport {code: $code})
                    SET a.name = $name,
                        a.city = $city,
                        a.country = $country,
                        a.runways = $runways
                """, parameters=airport_data)
                count += 1
        logger.info(f"Migrated {count} airports")
    
    def migrate_passengers(self):
        passengers = self.mongo_db.passengers.find()
        count = 0
        with self.neo4j_driver.session() as session:
            for passenger in passengers:
                session.run("""
                    MERGE (p:Passenger {passenger_id: $passenger_id})
                    SET p.full_name = $full_name,
                        p.passport = $passport,
                        p.nationality = $nationality,
                        p.email = $email,
                        p.phone = $phone
                """, parameters={
                    "passenger_id": passenger.get("passenger_id"),
                    "full_name": passenger.get("full_name"),
                    "passport": passenger.get("passport"),
                    "nationality": passenger.get("nationality"),
                    "email": passenger.get("contact", {}).get("email", ""),
                    "phone": passenger.get("contact", {}).get("phone", "")
                })
                count += 1
        logger.info(f"Migrated {count} passengers")
    
    def migrate_flights(self):
        flights = self.mongo_db.flights.find()
        count = 0
        with self.neo4j_driver.session() as session:
            for flight in flights:
                dep = flight.get("departure", {})
                arr = flight.get("arrival", {})
                
                dep_time = dep.get("time", datetime.utcnow())
                arr_time = arr.get("time", datetime.utcnow())
                
                flight_data = {
                    "flight_id": flight.get("flight_id"),
                    "airline_code": flight.get("airline", {}).get("code", ""),
                    "airline_name": flight.get("airline", {}).get("name", ""),
                    "status": flight.get("status", ""),
                    "departure_gate": dep.get("gate", ""),
                    "departure_airport": dep.get("airport", ""),
                    "arrival_airport": arr.get("airport", ""),
                    "departure_time": dep_time.isoformat(),
                    "arrival_time": arr_time.isoformat(),
                    "aircraft": flight.get("aircraft", ""),
                    "passengers": flight.get("passengers", [])
                }
                
                session.run("""
                    MERGE (f:Flight {flight_id: $flight_id})
                    SET f.airline_code = $airline_code,
                        f.airline_name = $airline_name,
                        f.status = $status,
                        f.departure_gate = $departure_gate,
                        f.departure_time = datetime($departure_time),
                        f.arrival_time = datetime($arrival_time)
                """, parameters=flight_data)
                
                if flight_data["departure_airport"]:
                    session.run("""
                        MATCH (f:Flight {flight_id: $flight_id})
                        MATCH (a:Airport {code: $departure_airport})
                        MERGE (f)-[:DEPARTS_FROM]->(a)
                    """, parameters=flight_data)
                
                if flight_data["arrival_airport"]:
                    session.run("""
                        MATCH (f:Flight {flight_id: $flight_id})
                        MATCH (a:Airport {code: $arrival_airport})
                        MERGE (f)-[:ARRIVES_AT]->(a)
                    """, parameters=flight_data)
                
                for passenger_id in flight_data["passengers"]:
                    session.run("""
                        MATCH (f:Flight {flight_id: $flight_id})
                        MATCH (p:Passenger {passenger_id: $passenger_id})
                        MERGE (p)-[:BOOKED_FLIGHT]->(f)
                    """, parameters={
                        "flight_id": flight_data["flight_id"],
                        "passenger_id": passenger_id
                    })
                
                count += 1
        logger.info(f"Migrated {count} flights with relations")
    
    def full_migration(self):
        logger.info("Starting MongoDB to Neo4j migration")
        self.clean_neo4j_database()
        self.create_neo4j_constraints()
        self.migrate_airports()
        self.migrate_passengers()
        self.migrate_flights()
        logger.info("Migration completed successfully")

if __name__ == "__main__":
    migrator = MongoNeo4jMigrator()
    migrator.full_migration()
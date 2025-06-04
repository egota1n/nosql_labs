from fastapi import APIRouter
from db.neo4j import get_neo4j_driver
from datetime import datetime

router = APIRouter(
    tags=["Routes"],
    prefix="/routes",
    responses={404: {"description": "Not found"}}
)

def format_flight(flight):
    return {
        "flight_id": flight.get("flight_id"),
        "airline_code": flight.get("airline_code"),
        "airline_name": flight.get("airline_name"),
        "status": flight.get("status"),
        "departure_gate": flight.get("departure_gate"),
        "departure_time": flight.get("departure_time").isoformat() if flight.get("departure_time") else None,
        "arrival_time": flight.get("arrival_time").isoformat() if flight.get("arrival_time") else None,
    }

def format_airport(airport):
    return {
        "code": airport.get("code"),
        "name": airport.get("name"),
        "city": airport.get("city"),
        "country": airport.get("country")
    }

# GET: /api/routes/{from_airport}/{to_airport} – Get Routes
@router.get("/{from_airport}/{to_airport}")
def get_routes(from_airport: str, to_airport: str):
    driver = get_neo4j_driver()
    results = []
    
    with driver.session() as session:
        direct_query = """
            MATCH (a1:Airport {code: $from_code})<-[:DEPARTS_FROM]-(f:Flight)-[:ARRIVES_AT]->(a2:Airport {code: $to_code})
            RETURN properties(f) AS flight,
                   properties(a1) AS departure_airport,
                   properties(a2) AS arrival_airport
        """
        direct_result = session.run(direct_query, from_code=from_airport, to_code=to_airport)
        
        for record in direct_result:
            results.append({
                "type": "direct",
                "flights": [format_flight(record["flight"])],
                "departure_airport": format_airport(record["departure_airport"]),
                "arrival_airport": format_airport(record["arrival_airport"]),
                "transfer_airports": []
            })
        
        one_stop_query = """
            MATCH (a1:Airport {code: $from_code})<-[:DEPARTS_FROM]-(f1:Flight)-[:ARRIVES_AT]->(via:Airport)
            MATCH (via)<-[:DEPARTS_FROM]-(f2:Flight)-[:ARRIVES_AT]->(a2:Airport {code: $to_code})
            WHERE f1.arrival_time < f2.departure_time
            RETURN properties(f1) AS first_flight,
                   properties(f2) AS second_flight,
                   properties(a1) AS departure_airport,
                   properties(a2) AS arrival_airport,
                   properties(via) AS transfer_airport
        """
        one_stop_result = session.run(one_stop_query, from_code=from_airport, to_code=to_airport)
        
        for record in one_stop_result:
            results.append({
                "type": "one_stop",
                "flights": [
                    format_flight(record["first_flight"]),
                    format_flight(record["second_flight"])
                ],
                "departure_airport": format_airport(record["departure_airport"]),
                "arrival_airport": format_airport(record["arrival_airport"]),
                "transfer_airports": [format_airport(record["transfer_airport"])]
            })
    
    return {
        "from": from_airport,
        "to": to_airport,
        "routes": results
    }
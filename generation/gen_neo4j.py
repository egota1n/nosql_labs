from cassandra.cluster import Cluster
from neo4j import GraphDatabase
from datetime import datetime

cassandra = Cluster(['127.0.0.1']).connect('airport')
rows = cassandra.execute("SELECT * FROM tickets")

neo4j = GraphDatabase.driver("neo4j://localhost:7687", 
                            auth=("neo4j", "test1234"))

with neo4j.session() as session:
    for row in rows:
        ticket = {
            "ticket_id": row.ticket_id,
            "passenger_id": row.passenger_id,
            "flight_id": row.flight_id,
            "seat": row.seat,
            "class_place":  row.class_place,
            "price": float(row.price),
            "booking_date": row.booking_date
        }
        
        if isinstance(ticket["booking_date"], datetime):
            ticket["booking_date"] = ticket["booking_date"].isoformat()
        
        session.run("""
            MERGE (p:Passenger {passenger_id: $passenger_id})
            MERGE (f:Flight {flight_id: $flight_id})
            MERGE (p)-[r:BOOKED_FLIGHT]->(f)
            SET r += {
                ticket_id: $ticket_id,
                seat: $seat,
                class_place: $class_place,
                price: $price,
                booking_date: datetime($booking_date)
            }
        """, parameters=ticket)
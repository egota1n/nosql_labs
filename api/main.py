from fastapi import FastAPI
from routers import aircrafts, passengers, tickets, routes

app = FastAPI(
    title="Airport REST API",
    description="API для работы с авиаданными",
    version="1.0"
)

app.include_router(aircrafts.router, prefix="/api")
app.include_router(passengers.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
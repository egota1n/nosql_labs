# NoSQL

### Лабораторная работа №4

Для реализации используется Python с FastApi, а также документация с помощью Swagger.

Для запуска необходимо выполнить команду:

```bash
python3 -m uvicorn main:app --reload --port 5010
```

После чего перейти по адресу: [https://localhost:5010/docs](http://localhost:5010/docs)

Всего 19 метод, из них 3 – POST, 10 – GET, 3 – PUT, 3 – DELETE.

#### Aircrafts

- **POST**: `/api/aircrafts` – Create Aircraft
    - Тело запроса model, manufacturer, capacity, status
- **GET**: `/api/aircrafts` – Get Aircrafts
    - Фильтрация по status, min_capacity, limit, offset
- **GET**: `/api/aircrafts/{reg_number}` – Get Aircraft
    - Входной параметр reg_number
- **PUT**: `/api/aircrafts/{reg_number}` – Update Aircraft
    - Входной параметр reg_number и тело запроса model, manufacturer, capacity, status
- **DELETE**: `/api/aircrafts/{reg_number}` – Delete Aircraft
    - Входной параметр reg_number

#### Passengers

- **POST**: `/api/passengers` – Create Passenger
    - Тело запроса full_name, passport, nationality, contact.email, contact.phone
- **GET**: `/api/passengers` – Get Passengers
    - Фильтрация по limit, offset
- **GET**: `/api/passengers/{passenger_id}` – Get Passenger
    - Входной параметр passenger_id
- **PUT**: `/api/passengers/{passenger_id}` – Update Passenger
    - Входной параметр passenger_id и тело запроса full_name, passport, nationality, contact.email, contact.phone
- **DELETE**: `/api/passengers/{passenger_id}` – Delete Passenger
    - Входной параметр passenger_id
- **GET**: `/api/passengers/stats/country` – Passenger statistics by country
    - Статистика пассажиров по странам
- **GET**: `/api/passengers/{passenger_id}/total_spent` – Get Passengers By Country
    - Статистика пассажира по потраченным средствам
- **GET**: `/api/passengers/{passenger_id}/travel_history` – Get Travel History
    - Информация о истории путешествия пассажира

#### Tickets

- **POST**: `/api/tickets` – Create Tickets
    - Тело запроса passenger_id, flight_id, seat, class_place, price
- **GET**: `/api/tickets` – Get Tickets
    - Фильтрация по passenger_id, flight_id, limit, offset
- **GET**: `/api/tickets/{reg_number}` – Get Ticket
    - Входной параметр reg_number
- **PUT**: `/api/tickets/{reg_number}` – Update Ticket
    - Входной параметр reg_number и тело запроса passenger_id, flight_id, seat, class_place, price
- **DELETE**: `/api/tickets/{reg_number}` – Delete Ticket
    - Входной параметр reg_number

#### Routes

- **GET**: /api/routes/{from_airport}/{to_airport} – Get Routes
    - Информация о маршруте между аэропортами
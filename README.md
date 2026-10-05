# Orders API

A small containerised API intended for cloud infrastructure labs.

The point of the project is **not** to become a Python developer.

Your job is to look at the application and work out what infrastructure it
requires in order to run correctly in Azure.

## What the application does

It exposes a REST API that lets users:

- Create an order
- List orders
- Retrieve a specific order
- Update an order status
- Delete an order
- Check application health
- Check whether the application is ready to serve traffic

The application stores orders in PostgreSQL.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Basic service information |
| GET | `/health` | Application liveness |
| GET | `/ready` | Application + database readiness |
| POST | `/orders` | Create an order |
| GET | `/orders` | List orders |
| GET | `/orders/{id}` | Retrieve an order |
| PATCH | `/orders/{id}/status` | Change order status |
| DELETE | `/orders/{id}` | Delete an order |

FastAPI also automatically exposes interactive API documentation at:

`/docs`

## Run locally

The easiest way:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:8000/docs
```

Health:

```bash
curl http://localhost:8000/health
```

Readiness:

```bash
curl http://localhost:8000/ready
```

Create an order:

```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Mahin",
    "product": "Mechanical Keyboard",
    "quantity": 1
  }'
```

List orders:

```bash
curl http://localhost:8000/orders
```

## Your infrastructure exercise

Before building anything in Azure, inspect:

- `Dockerfile`
- `.env.example`
- `docker-compose.yml`
- `app/main.py`

Work out what the application needs from its infrastructure.

Think about:

- What actually runs the application?
- What image needs to exist?
- What port must receive traffic?
- What environment variables are required?
- Which environment variable is absolutely mandatory?
- Does the application need persistent storage?
- Does the application need a database?
- What type?
- Does the application need to be reachable from the internet?
- Which endpoint should be used for a liveness probe?
- Which endpoint should be used for a readiness probe?
- What would happen if the database disappeared?
- What parts should Azure manage rather than putting inside the application container?

Do not worry about making the architecture secure yet.

First objective:

> Get the application running successfully in Azure.

Then improve the architecture in stages.

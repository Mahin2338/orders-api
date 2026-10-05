import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

APP_ENV = os.getenv("APP_ENV", "development")
PORT = int(os.getenv("PORT", "8000"))


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("orders-api")


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(100))
    product: Mapped[str] = mapped_column(String(150))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# API Models
# ---------------------------------------------------------

class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    product: str = Field(min_length=2, max_length=150)
    quantity: int = Field(gt=0, le=100)


class OrderResponse(BaseModel):
    id: int
    customer_name: str
    product: str
    quantity: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pending|processing|shipped|cancelled)$")


# ---------------------------------------------------------
# Application
# ---------------------------------------------------------

app = FastAPI(
    title="Orders API",
    version="1.0.0",
    description="Simple order-management API for infrastructure labs.",
)


@app.on_event("startup")
def startup():
    logger.info("Starting Orders API in %s environment", APP_ENV)

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database connection successful")
    except Exception:
        logger.exception("Failed to initialise database")
        raise


@app.get("/")
def root():
    return {
        "service": "orders-api",
        "environment": APP_ENV,
        "status": "running",
    }


@app.get("/health")
def health():
    """
    Basic liveness endpoint.

    This only proves the application process itself is alive.
    """
    return {"status": "ok"}


@app.get("/ready")
def readiness(db: Session = Depends(get_db)):
    """
    Readiness endpoint.

    This checks whether the application can actually reach its database.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
        }
    except SQLAlchemyError:
        logger.exception("Database readiness check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    new_order = Order(
        customer_name=order.customer_name,
        product=order.product,
        quantity=order.quantity,
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    logger.info(
        "Created order id=%s customer=%s product=%s",
        new_order.id,
        new_order.customer_name,
        new_order.product,
    )

    return new_order


@app.get("/orders", response_model=list[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(Order.id.desc()).all()


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@app.patch("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    update: OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = update.status
    db.commit()
    db.refresh(order)

    logger.info(
        "Updated order id=%s status=%s",
        order.id,
        order.status,
    )

    return order


@app.delete(
    "/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(order)
    db.commit()

    logger.info("Deleted order id=%s", order_id)

from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Text, TIMESTAMP,Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# from .models import Base  # Ensure this imports from the correct place
from sqlalchemy.ext.declarative import declarative_base
from src.routers.users.models.users import User
from sqlalchemy import Column, DateTime
from datetime import datetime, timezone


Base = declarative_base()

class Payment(Base):
    __tablename__ = 'payments'
    __table_args__ = {'schema': 'voice_bot'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    cf_link_id = Column(String(50), unique=True)  # Cashfree generated ID
    transaction_id = Column(String(100), unique=True, nullable=True)  # Optional transaction ID
    link_id = Column(String(50))  # Newly added column
    link_url = Column(Text)  # Payment link URL
    amount = Column(Numeric(10,2), nullable=False)  # Payment Amount
    currency = Column(String(10), default="INR")  # Currency (Default INR)
    status = Column(String(20))  # Payment Status
    link_status = Column(String(20))  # Link Status (ACTIVE, EXPIRED, etc.)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    plan_type = Column(String)  # ✅ Add this
    subscription_end = Column(DateTime(timezone=True))



    def __repr__(self):
        return f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.status})>"


# src/models/daily_notification.py
class DailyNotification(Base):
    __tablename__ = "daily_notifications"

    id = Column(Integer, primary_key=True, index=True)
    notification_type = Column(String, unique=True)
    last_sent_date = Column(Date)

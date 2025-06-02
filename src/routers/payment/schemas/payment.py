from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime

# Schema for creating a payment link request
class CreatePaymentLinkSchema(BaseModel):
    amount: float = Field(..., gt=0)  # Ensure amount is greater than 0
    currency: str = Field(default="INR", max_length=3)
    link_purpose: str = Field(..., max_length=255)
    notify_url: Optional[HttpUrl] = None
    return_url: Optional[HttpUrl] = None
    customer_name: str = Field(..., max_length=100)
    customer_email: str
    customer_phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")  # E.164 format
    plan_type: str

# Schema for storing the response when a payment link is created
class PaymentLinkResponseSchema(BaseModel):
    success: bool
    status: int
    message: str
    cf_link_id: str
    link_id: str
    user_id: int
    link_url: HttpUrl
    amount: float
    currency: str
    link_status: str
    created_at: datetime

# Schema for Webhook Payment Update
class PaymentWebhookSchema(BaseModel):
    cf_link_id: str  # Cashfree's unique payment link ID
    transaction_id: Optional[str]  # Transaction ID if payment is successful
    amount_paid: float
    payment_status: str  # Expected: "success", "failed", or "pending"
    payment_time: datetime

# Schema for updating the payment table based on webhook response
class UpdatePaymentSchema(BaseModel):
    cf_link_id: str
    transaction_id: Optional[str]
    amount_paid: float
    payment_status: str
    
# Request body schema
class ReminderRequest(BaseModel):
    user_id: int
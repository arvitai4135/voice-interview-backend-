import os
import enum
import uuid
import requests
from . import  utilities
from sqlalchemy import func
from dotenv import load_dotenv
from src.database import Database
from sqlalchemy.orm import Session
from loguru import logger as logging
from src.routers.users.models import User
from src.utils.jwt import get_email_from_token
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone, timedelta
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
from src.routers.payment.models import Payment,DailyNotification
from fastapi import APIRouter, Depends, HTTPException, Request, Body,status
from src.routers.payment.schemas import CreatePaymentLinkSchema, PaymentWebhookSchema,ReminderRequest

load_dotenv()

X_API_VERSION = os.getenv('X_API_VERSION') 
X_CLIENT_ID = os.getenv('X_CLIENT_ID')
X_CLIENT_SECRET = os.getenv('X_CLIENT_SECRET')
# X_API_VERSION = ""
# X_CLIENT_ID = ""
# X_CLIENT_SECRET ="" 


# Dependency to get database session
db_util = Database()
def get_db():
    db = db_util.get_session()
    try:
        yield db
    finally:
        db.close()

# Define router
router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"],
    responses={404: {"description": "Not found"}},
)

# Payment Status Enum
class PaymentStatusEnum(str, enum.Enum):
    pending = "pending"
    successful = "successful"
    failed = "failed"

@router.post("/create-payment-link", response_model=dict)
def create_payment_link(
    request: Request,
    request_data: CreatePaymentLinkSchema = Body(...),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    API to generate a Cashfree payment link and store/update details in the database.
    """

    logging.debug("Create payment link function called")

    auth_header = request.headers.get("Authorization")
    if not auth_header or "Bearer " not in auth_header:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

    token = auth_header.split(" ")[1]
    email = get_email_from_token(token)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found, cannot create appointment",
        )

    # Plan durations in months
    plan_months = {
        "one_month": 1,
        "two_months": 2,
        "three_months": 3,
        "six_months": 6,
        "single_meal": 0,
        "weekly_meal_plan": 0,
        "monthly_meal_plan": 1,
        "custom": 0,
    }

    if request_data.plan_type not in plan_months:
        raise HTTPException(status_code=400, detail="Invalid plan_type")

    meal_plans = ["single_meal", "weekly_meal_plan", "monthly_meal_plan"]
    month_plans = ["one_month", "two_months", "three_months", "six_months"]

    is_meal_plan = request_data.plan_type in meal_plans
    is_month_plan = request_data.plan_type in month_plans

    expiry_time = datetime.now(timezone.utc) + timedelta(hours=24)
    formatted_expiry_time = expiry_time.isoformat(timespec="seconds")

    unique_id = uuid.uuid4().hex  # Generate a unique identifier
    link_id = f"{user.id}_{unique_id}"

    payload = {
        "customer_details": {
            "customer_email": request_data.customer_email,
            "customer_name": request_data.customer_name,
            "customer_phone": request_data.customer_phone,
        },
        "link_amount": request_data.amount,
        "link_currency": request_data.currency,
        "link_expiry_time": formatted_expiry_time,
        "link_purpose": request_data.link_purpose,
        "link_id": link_id,
        "link_meta": {
            "notify_url": "https://ee08e626ecd88c61c85f5c69c0418cb5.m.pipedream.net",
            "return_url": "https://nutridietmitra.com/order-confirmation",
        },
        "link_notify": {"send_email": True},
    }

    headers = {
        "x-api-version": X_API_VERSION,
        "x-client-id": X_CLIENT_ID,
        "x-client-secret": X_CLIENT_SECRET,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post("https://sandbox.cashfree.com/pg/links", json=payload, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Failed to create payment link: {e}")
        raise HTTPException(status_code=400, detail="Failed to create payment link")

    response_data = response.json()
    logging.info(f"Payment link created successfully: {response_data}")

    # Check existing payments
    previous_payments = db.query(Payment).filter(
        Payment.user_id == user.id,
    ).all()

    matching_payment = None

    # Check if any previous record is of the same plan_type
    for payment in previous_payments:
        if payment.plan_type == request_data.plan_type:
            matching_payment = payment
            break

    # Check if category (meal or month) changed
    category_changed = False
    for payment in previous_payments:
        if (
            (payment.plan_type in meal_plans and request_data.plan_type in month_plans)
            or (payment.plan_type in month_plans and request_data.plan_type in meal_plans)
        ):
            category_changed = True
            break

    if matching_payment and not category_changed:
        # Same plan_type and same category -> update existing record
        logging.info(f"Updating existing payment for user_id={user.id}, plan_type={request_data.plan_type}")

        matching_payment.cf_link_id = response_data["cf_link_id"]
        matching_payment.link_id = response_data["link_id"]
        matching_payment.link_url = response_data["link_url"]
        matching_payment.amount = request_data.amount
        matching_payment.currency = request_data.currency
        matching_payment.link_status = PaymentStatusEnum.pending

        if is_month_plan:
            if matching_payment.subscription_end and matching_payment.subscription_end > datetime.now(timezone.utc):
                matching_payment.subscription_end += timedelta(days=30 * plan_months[request_data.plan_type])
            else:
                matching_payment.subscription_end = datetime.now(timezone.utc) + timedelta(days=30 * plan_months[request_data.plan_type])
        else:
            matching_payment.subscription_end = None

    else:
        # Different plan or category changed -> create new payment
        logging.info(f"Creating new payment for user_id={user.id}, plan_type={request_data.plan_type}")

        subscription_end = None
        if is_month_plan:
            subscription_end = datetime.now(timezone.utc) + timedelta(days=30 * plan_months[request_data.plan_type])

        new_payment = Payment(
            user_id=user.id,
            cf_link_id=response_data["cf_link_id"],
            link_id=response_data["link_id"],
            link_url=response_data["link_url"],
            amount=request_data.amount,
            currency=request_data.currency,
            link_status=PaymentStatusEnum.pending,
            plan_type=request_data.plan_type,
            subscription_end=subscription_end,
        )
        db.add(new_payment)

    db.commit()

    return {
        "success": True,
        "status": 201,
        "message": "Payment link created successfully",
        "data": {"link_url": response_data["link_url"]}
    }

# ------------------- 2️⃣ Webhook - Update Payment -------------------
@router.post("/cashfree-webhook")
async def cashfree_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Webhook API to update payment status based on Cashfree's response.
    """
    logging.debug("Webhook function called")

    try:
        data = await request.json()
        logging.info(f"Received Webhook Data: {data}")

        payment_data = data.get("data", {})
        order_data = payment_data.get("order", {})

        cf_link_id = str(payment_data.get("cf_link_id", ""))
        link_id = payment_data.get("link_id", "")
        transaction_id = str(order_data.get("transaction_id", ""))
        amount_paid = float(payment_data.get("link_amount_paid", 0))
        payment_status = order_data.get("transaction_status", "").lower()
        logging.error(f"Payment_status is :{payment_status}")

        # Map payment status
        status_map = {"success": PaymentStatusEnum.successful, "failed": PaymentStatusEnum.failed, "pending": PaymentStatusEnum.pending}
        payment_status_data = status_map.get(payment_status, PaymentStatusEnum.pending)

        # Find the existing payment record
        payment = db.query(Payment).filter(Payment.cf_link_id == cf_link_id).first()
        if not payment:
            logging.warning(f"Webhook: No matching payment found for cf_link_id {cf_link_id}")
            raise HTTPException(status_code=404, detail="Payment record not found")

        # Update payment record
        payment.transaction_id = transaction_id
        payment.amount_paid = amount_paid
        payment.status = payment_status
        payment.link_status = payment_status
        payment.updated_at = func.current_timestamp()

        db.commit()

        logging.info(f"Payment {cf_link_id} updated successfully to {payment_status}")

        return {
            "success": True,
            "status": 200,
            "message": "Payment record updated",
            "data": {"status": payment_status}
        }

    except Exception as e:
        logging.error(f"Error in webhook processing: {e}")
        return {
            "success": False,
            "status": 500,
            "message": "An unexpected error occurred",
            "data": None
        }


@router.get("/history", status_code=200)
def get_payment_history(request: Request, db: Session = Depends(get_db)):
    """
    Admin endpoint to get payment history with user details.
    """
    try:
        # Get the email from the token
        token = request.headers.get("Authorization")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization token missing",
            )
        token = token.split(" ")[1]  # Assuming token is passed as "Bearer <token>"
        email = get_email_from_token(token)

        # Check if the user is an admin
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {
                "success": False,
                "status": 404,
                "message": "Admin user not found",
                "data": None
            }

        if user.role != "admin":
            return {
                "success": False,
                "status": 403,
                "message": "You are not authorized to access this resource",
                "data": None
            }

        # Query all payments
        payments = db.query(Payment).all()

        if not payments:
            return {
                "success": False,
                "status": 404,
                "message": "No payment records found",
                "data": None
            }

        # Prepare payment history list
        payment_history = []
        for payment in payments:
            # Get user details linked to this payment
            linked_user = db.query(User).filter(User.id == payment.user_id).first()

            if not linked_user:
                continue  # Skip if user doesn't exist (shouldn't normally happen)

            payment_history.append({
                "user_id":linked_user.id,
                "name": linked_user.full_name,
                "email": linked_user.email,
                "phone_number": linked_user.phone_number,
                "payment_id":payment.id,
                "address": None, # if payment.address else None,
                "play_type": payment.plan_type,
                "price": payment.amount,
                "start_date": payment.created_at.strftime('%b %d, %Y, %I:%M %p') if payment.created_at else None,
                "end_date": payment.subscription_end.strftime('%b %d, %Y, %I:%M %p') if payment.subscription_end else None,
            })


        return {
            "success": True,
            "status": 200,
            "message": "Payment history fetched successfully",
            "data": payment_history
        }

    except Exception as e:
        logging.error(f"An error occurred while fetching payment history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        )


@router.post("/send-subscription-reminder", status_code=200)
def send_subscription_reminder(request_data: ReminderRequest, request: Request, db: Session = Depends(get_db)):
    """
    Endpoint to send subscription expiry reminder email to a particular user based on user_id.
    """
    try:
        # Authorization check
        token = request.headers.get("Authorization")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization token missing",
            )
        token = token.split(" ")[1]  # Assuming token is passed as "Bearer <token>"
        email = get_email_from_token(token)

        # Verify if user is admin
        admin_user = db.query(User).filter(User.email == email).first()
        if not admin_user:
            return {
                "success": False,
                "status": 404,
                "message": "Admin user not found",
                "data": None
            }

        if admin_user.role != "admin":
            return {
                "success": False,
                "status": 403,
                "message": "You are not authorized to access this resource",
                "data": None
            }

        # Get the user and their latest payment info
        user = db.query(User).filter(User.id == request_data.user_id).first()
        if not user:
            return {
                "success": False,
                "status": 404,
                "message": "User not found",
                "data": None
            }

        payment = db.query(Payment).filter(Payment.user_id == user.id).order_by(Payment.created_at.desc()).first()
        if not payment:
            return {
                "success": False,
                "status": 404,
                "message": "No payment record found for this user",
                "data": None
            }

        today = datetime.now(payment.subscription_end.tzinfo)


        if not payment.subscription_end:
            return {
                "success": False,
                "status": 400,
                "message": "User's subscription end date not available",
                "data": None
            }

        # Calculate days left
        days_left = (payment.subscription_end - today).days

        if days_left < 0:
            return {
                "success": False,
                "status": 400,
                "message": "User's subscription has already expired",
                "data": None
            }

        # Prepare email content
        subject = "Subscription Expiry Reminder!"
        body = f"""
            Dear {user.full_name},

            We hope this message finds you well.

            This is a kind reminder from Nutridiet Mitra that your subscription is set to expire on {payment.subscription_end.strftime('%B %d, %Y')}.  
            You have {days_left} days remaining on your current plan.

            To continue enjoying uninterrupted access to our personalized diet plans, expert consultations, and premium services, we encourage you to renew your subscription before it expires.

            Renew today and stay committed to your health journey with Nutridiet Mitra!

            If you have any questions or need assistance, feel free to reach out to us.

            Warm regards,  
            The Nutridiet Mitra Team
            www.nutridietmitra.com
        """

        # Send email
        try:
            utilities.send_email(
                to_email=user.email,
                subject=subject,
                body=body
            )
        except Exception as e:
            logging.error(f"Failed to send email to {user.email}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email. Please try again later.",
            )

        return {
            "success": True,
            "status": 200,
            "message": f"Reminder email sent to {user.email} ({days_left} days left)",
            "data": {
                "user_id": user.id,
                "email": user.email,
                "days_left": days_left
            }
        }

    except Exception as e:
        logging.error(f"An error occurred while sending subscription reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        )
        

@router.get("/get-expiring-subscriptions", status_code=200)
def get_expiring_subscriptions(request: Request, db: Session = Depends(get_db)):
    try:
        # Authorization check
        token = request.headers.get("Authorization")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization token missing",
            )
        token = token.split(" ")[1]
        email = get_email_from_token(token)

        # Check if admin
        admin_user = db.query(User).filter(User.email == email).first()
        if not admin_user:
            return {
                "success": False,
                "status": 404,
                "message": "Admin user not found",
                "data": None
            }

        if admin_user.role != "admin":
            return {
                "success": False,
                "status": 403,
                "message": "You are not authorized to access this resource",
                "data": None
            }

        today = datetime.now(timezone.utc)  # <-- timezone aware
        next_week = today + timedelta(days=7)

        expiring_payments = db.query(Payment).filter(
            Payment.subscription_end >= today,
            Payment.subscription_end <= next_week
        ).all()

        users_data = []
        for payment in expiring_payments:
            user = db.query(User).filter(User.id == payment.user_id).first()
            if not user:
                continue

            days_left = (payment.subscription_end - today).days  # ✅ will work now

            users_data.append({
                "user_id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "subscription_end": payment.subscription_end.strftime("%Y-%m-%d"),
                "days_left": days_left
            })


        # 🛡️ Check last sent date from DB
        notification = db.query(DailyNotification).filter_by(notification_type="expiring_subscriptions").first()

        if not notification or notification.last_sent_date != today:
            # First time today -> Send mail
            if users_data:
                html_body = "<h3>Upcoming Subscription Expirations</h3><ul>"
                for user_data in users_data:
                    html_body += f"<li><strong>{user_data['full_name']}</strong> ({user_data['email']}) - Subscription ends on {user_data['subscription_end']} ({user_data['days_left']} days left)</li>"
                html_body += "</ul>"

                utilities.send_email(
                    subject="⚡ Expiring User Subscriptions Alert",
                    to_email=admin_user.email,   # ✅ corrected from `to` to `to_email`
                    body=html_body,
                    is_html=True
                )


            # 🔥 Update or Insert today's date
            if not notification:
                notification = DailyNotification(notification_type="expiring_subscriptions", last_sent_date=today)
                db.add(notification)
            else:
                notification.last_sent_date = today
            db.commit()

        return {
            "success": True,
            "status": 200,
            "message": "Expiring users fetched successfully.",
            "data": users_data
        }

    except Exception as e:
        logging.error(f"An error occurred while fetching expiring subscriptions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        )

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from loguru import logger as logging
from src.database import Database
from src.utils.jwt import get_email_from_token
from fastapi.security import OAuth2PasswordBearer
# from . import models
from src.routers.users.models import User as users_model
from src.routers.payment.models import Payment
from . import schema
from typing import List

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database dependency
db_util = Database()

def get_db():
    db = db_util.get_session()
    try:
        yield db
    finally:
        db.close()



# Dependency to ensure admin role
def get_admin_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = get_email_from_token(token)
    user = db.query(users_model).filter(users_model.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    print(f"user.role---{user.id}---{user.role}")

    # Check if user.role is a string or Enum instance
    if isinstance(user.role, str):
        if user.role.lower() != "admin":  # Direct string comparison
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required."
            )

    return user

# Admin router
admin_router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    responses={404: {"description": "Not found"}},
)

# API to list all users (active and inactive)
@admin_router.get("/users", response_model=schema.AdminUserListResponse)
def list_all_users(db: Session = Depends(get_db), admin_user = Depends(get_admin_user)):
    """
    Retrieve a list of all users (active and inactive) for admin panel.
    """
    try:
        users = db.query(users_model).all()
        return {
            "success": True,
            "status": 200,
            "message": "Users retrieved successfully",
            "data": users
        }
    except Exception as e:
        logging.error(f"Error retrieving users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving users."
        )

# API to edit user details
@admin_router.put("/users/{user_id}", response_model=schema.AdminUserResponse)
def update_user(
    user_id: int,
    updated_user: schema.AdminUpdateUserSchema = Body(...),
    db: Session = Depends(get_db),
    admin_user = Depends(get_admin_user)
):
    """
    Update user details (full edit) by admin.
    """
    try:
        user = db.query(users_model).filter(users_model.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        # Update fields dynamically based on provided data
        for field, value in updated_user.dict(exclude_unset=True).items():
            if field == "password" and value:
                user.set_password(value)  # Hash the password if provided
            elif field in ["full_name", "email", "phone_number", "profile_path", "status", "role"]:
                setattr(user, field, value)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Field '{field}' cannot be updated."
                )

        db.commit()
        db.refresh(user)
        return {
            "success": True,
            "status": 200,
            "message": "User updated successfully",
            "data": user
        }
    except ValueError as ve:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(ve)}"
        )
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the user."
        )

# API to list all appointments (active and inactive)
@admin_router.get("/appointments", response_model=schema.AdminAppointmentListResponse)
def list_all_appointments(db: Session = Depends(get_db), admin_user = Depends(get_admin_user)):
    """
    Retrieve a list of all appointments (active and inactive) for admin panel.
    """
    try:
        appointments = db.query(Appointment).all()
        return {
            "success": True,
            "status": 200,
            "message": "Appointments retrieved successfully",
            "data": appointments
        }
    except Exception as e:
        logging.error(f"Error retrieving appointments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving appointments."
        )

# API to edit appointment details
@admin_router.put("/appointments/{appointment_id}", response_model=schema.AdminAppointmentResponse)
def update_appointment(
    appointment_id: int,
    updated_appointment: schema.AdminUpdateAppointmentSchema = Body(...),
    db: Session = Depends(get_db),
    admin_user = Depends(get_admin_user)
):
    """
    Update appointment details (full edit) by admin.
    """
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found."
            )

        # Update fields dynamically based on provided data
        for field, value in updated_appointment.dict(exclude_unset=True).items():
            if field in ["name", "email", "mobile_number", "medical_issue", "message", "status"]:
                setattr(appointment, field, value)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Field '{field}' cannot be updated."
                )

        db.commit()
        db.refresh(appointment)
        return {
            "success": True,
            "status": 200,
            "message": "Appointment updated successfully",
            "data": appointment
        }
    except ValueError as ve:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(ve)}"
        )
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating appointment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the appointment."
        )
    
# API to list all pending and successful payments
@admin_router.get("/payments", response_model=schema.AdminPaymentListResponse)
def list_payments_by_status(
    status: str,  # Query parameter for payment status ("pending" or "success")
    db: Session = Depends(get_db),
    admin_user = Depends(get_admin_user)
):
    """
    Retrieve a list of all payments filtered by status (pending or success) for the admin panel.
    """
    try:
        if status.lower() not in ["pending", "successful"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Use 'pending' or 'success'."
            )
        
        payments = db.query(Payment).filter(Payment.link_status == status.lower()).all()
        print(f"payments---------{payments}")
        return {
            "success": True,
            "status": 200,
            "message": f"{status.capitalize()} payments retrieved successfully",
            "data": payments
        }
    except Exception as e:
        logging.error(f"Error retrieving {status} payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while retrieving {status} payments."
        )
from sqlalchemy import func, and_
from datetime import datetime, timedelta

@admin_router.get("/payments/expiring", response_model=schema.AdminPaymentListResponse)
def list_expiring_payments(
    db: Session = Depends(get_db),
    admin_user = Depends(get_admin_user)
):
    """
    Retrieve the latest successful payment for each user where the subscription is expiring within 2 days.
    """
    try:
        # Current UTC time + 2 days
        threshold_date = datetime.utcnow() + timedelta(days=2)

        # Subquery to get the latest payment for each user
        subquery = (
            db.query(
                Payment.user_id,
                func.max(Payment.created_at).label("latest_payment")
            )
            .filter(
                and_(
                    Payment.link_status == "successful",
                    Payment.subscription_end <= threshold_date
                )
            )
            .group_by(Payment.user_id)
            .subquery()
        )

        # Join back to Payment to get full records
        payments = (
            db.query(Payment)
            .join(
                subquery,
                and_(
                    Payment.user_id == subquery.c.user_id,
                    Payment.created_at == subquery.c.latest_payment
                )
            )
            .all()
        )

        return {
            "success": True,
            "status": 200,
            "message": "Expiring payments retrieved successfully",
            "data": payments
        }

    except Exception as e:
        logging.error(f"Error retrieving expiring payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving expiring payments."
        )

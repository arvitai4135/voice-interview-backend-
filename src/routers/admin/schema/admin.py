from pydantic import BaseModel, EmailStr, Field, condecimal
from typing import Optional, List
from datetime import datetime
import enum

# Enum for user role and status (reusing from your existing code)
class UserRoleEnum(str, enum.Enum):
    admin = "admin"
    user = "user"

class UserStatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"

# Schema for updating user details (full edit for admin)
class AdminUpdateUserSchema(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    password: Optional[str] = Field(None, min_length=8)
    profile_path: Optional[str] = None
    status: Optional[UserStatusEnum] = None
    role: Optional[UserRoleEnum] = None

# Schema for user data in response
class AdminUserData(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: Optional[str]
    profile_path: Optional[str]
    status: UserStatusEnum
    role: UserRoleEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Response schema for listing all users
class AdminUserListResponse(BaseModel):
    success: bool
    status: int
    message: str
    data: List[AdminUserData]

# Response schema for single user edit
class AdminUserResponse(BaseModel):
    success: bool
    status: int
    message: str
    data: AdminUserData



# Enum for appointment status (reusing from your existing code)
class AppointmentStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"

# Schema for updating appointment details (full edit for admin)
class AdminUpdateAppointmentSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    medical_issue: Optional[str] = None
    message: Optional[str] = None
    status: Optional[AppointmentStatus] = None

# Schema for appointment data in response
class AdminAppointmentData(BaseModel):
    id: int
    name: str
    email: EmailStr
    mobile_number: str
    medical_issue: str
    message: Optional[str]
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Response schema for listing all appointments
class AdminAppointmentListResponse(BaseModel):
    success: bool
    status: int
    message: str
    data: List[AdminAppointmentData]

# Response schema for single appointment edit
class AdminAppointmentResponse(BaseModel):
    success: bool
    status: int
    message: str
    data: AdminAppointmentData


class AdminPaymentResponse(BaseModel):
    id: int
    user_id: int
    cf_link_id: Optional[str]
    transaction_id: Optional[str]
    link_id: Optional[str]
    link_url: Optional[str]
    amount: condecimal(max_digits=10, decimal_places=2)
    currency: str
    status: str
    link_status: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class AdminPaymentListResponse(BaseModel):
    success: bool
    status: int
    message: str
    data: List[AdminPaymentResponse]
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
import enum


# Enum for user status
class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    

class UserResponseData(BaseModel):
    id: Optional[int] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    profile_path: Optional[str] = None
    status: Optional[str] = None
    role: Optional[str] = None  # Add role if necessary for admins
    
     

    class Config:
        orm_mode = True

# Request schema for updating the profile path
class UpdateProfilePathRequest(BaseModel):
    profile_path: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: Optional[str]
    profile_path: Optional[str]

    class Config:
        orm_mode = True

class UserRoleEnum(str, enum.Enum):
    admin = "admin"
    user = "user"

class UserStatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"

class CreateUserSchema(BaseModel):
    full_name: str = Field(..., max_length=100)
    email: EmailStr
    phone_number: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")  # Use pattern instead of regex
    password: str = Field(..., min_length=8)
    profile_path: Optional[str] = "profile_pictures/default.png"
    status: UserStatusEnum = UserStatusEnum.active
    

class LoginSchema(BaseModel):
    email: str
    password : str


class TokenResponse(BaseModel):
    success: bool
    status: int
    isActive: bool
    message: str
    data: Optional[dict]  # Data can be None or a dictionary

class PlanInfo(BaseModel):
    plan_type: Optional[str]
    plan_name: Optional[str]
    plan_category: Optional[str]

    class Config:
        orm_mode = True
        
class UserData(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    profile_path: Optional[str]
    role : Optional[str] = None
    status: str
    
    # Add these:
    # New fields
    meal_plan: Optional[PlanInfo] = None
    subscription_plan: Optional[PlanInfo] = None
    
    class Config:
        orm_mode = True  # Ensures compatibility with SQLAlchemy models
        # Ensure that datetime fields are serialized as strings
        json_encoders = {
            datetime: lambda v: v.isoformat()  # Converts datetime to ISO 8601 string format
        }


class UserResponse(BaseModel):
    success: bool
    status: int
    isActive: bool
    message: str
    data: UserData

class UserProfilePathResponse(BaseModel):
    success: bool
    status: int
    message: str
    data: dict

class ChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str
    
class ForgotPasswordSchema(BaseModel):
    email: EmailStr

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str
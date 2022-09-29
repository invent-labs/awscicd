from enum import Enum
from typing import Optional, List

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field

from app.models.base import PyObjectId


class UserModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(...)
    email: EmailStr = Field(...)
    password: str = Field(...)
    signed_up_ts: int
    updated_ts: int
    role: Optional[str] = None
    status: Optional[str] = None
    is_deleted: bool = False

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "Jane Doe",
                "email": "jdoe@example.com",
                "password": "test",
            }
        }


class SignupModel(BaseModel):
    name: str = Field(...)
    email: EmailStr = Field(...)
    phone: str = Field(...)
    password: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "jdoe@example.com",
                "phone": "+911234567890",
                "password": "test",
            },
        }


class LoginModel(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "email": "jdoe@example.com",
                "password": "test"
            }
        }


class SetPasswordLoginModel(BaseModel):
    user_id: str = Field(...)
    code: str = Field(...)
    name: str = Field(...)
    password: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "user_id": "user_id",
                "code": "activation code",
                "name": "user name",
                "password": "test"
            }
        }


class DeleteModel(BaseModel):
    password: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {"example": {"password": "test"}}


class LoginResponseModel(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    email: EmailStr = Field(...)
    role: str = Field(...)
    access_token: str = Field(...)
    access_token_expiry: int = Field(...)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserInDB(UserModel):
    hashed_password: str


class ChangePasswordModel(BaseModel):
    current_password: str = Field(...)
    new_password: str = Field(...)


class ResetPasswordModel(BaseModel):
    email: str = Field(...)
    new_password: str = Field(...)
    otp: str = Field(...)


class ForgotPasswordModel(BaseModel):
    email: EmailStr


class UpdateUserModel(BaseModel):
    name: str
    email: Optional[EmailStr]

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "jdoe@example.com",
            }
        }


class InviteUserModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    email: str = Field(...)
    role: str = Field(...)
    invited_id: str
    invitation_expiry_time: int = Field(...)
    activation_code: str = Field(...)
    status: str
    signed_up_ts: int
    is_invited: bool = False
    is_deleted: bool = False

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "email": "jdoe@example.com",
                "role": "test"
            }
        }


class InviteUpdateModel(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr = Field(...)
    role: str

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "firstname": "name",
                "lastname": "last_name",
                "email": "jdoe@example.com",
                "role": "test",
            }
        }


class UserRole(str, Enum):
    business_admin = "admin"
    super_admin = "super_admin"
    business_user = "user"


class UserActionType(str, Enum):
    user_invite = "User Invite"


UserActionMatrix = {
    "super_admin": [
        "USERS.LIST", "USERS.CREATE", "USERS.READ", "USERS.UPDATE",
        "USERS.DELETE"
    ],
    "admin": [
        "RESTAURANT.LIST", "RESTAURANT.CREATE", "RESTAURANT.READ",
        "RESTAURANT.UPDATE", "RESTAURANT.DELETE"
    ]
}

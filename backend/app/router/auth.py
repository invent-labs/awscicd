import os
from datetime import timedelta, datetime
from random import randint
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from starlette import status
from starlette.responses import JSONResponse

from app.db.base import users_collection_pymongo, users_collection
# from app.managers.email_managers import get_email_template, EmailTemplate
from app.models.user import ForgotPasswordModel, UserModel, LoginModel, LoginResponseModel, SignupModel, \
    ResetPasswordModel, ChangePasswordModel, SetPasswordLoginModel, UserRole, UserActionMatrix
# from app.utils.emails import MailRequest, send_email
from app.utils.utils import get_error_response, get_timestamp

from app.config import settings

router = APIRouter(
    prefix="/business",
    tags=["auth"],
    responses={404: {
        "description": "Not found"
    }},
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/business/token")

SECRET_KEY = "608f5343c5c67d9f1e65aabfce03f2a3777197fdfe0a89cf7b3bde37eab2453c"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 2880
OTP_EXPIRE_MINUTES = 5


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


def get_user(email: str) -> object:
    user = users_collection_pymongo.find_one({
        "email": email,
        "is_deleted": False
    })
    return user


def get_user_by_id(user_id: str) -> object:
    user = users_collection_pymongo.find_one({"_id": user_id})
    return user


def authenticate_user(email: str, password: str) -> object:
    user: object = get_user(email)
    if not user:
        return None
    if not verify_password(password, user.get("password")):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = str(payload.get("sub"))
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user(str(token_data.email))
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
        current_user: UserModel = Depends(get_current_user)):
    return current_user


class APIResponseModel(BaseModel):
    status: bool
    message: Optional[str]


@router.get("/", description="Home")
async def homepage():
    response = APIResponseModel(
        status=True,
        message=f"{settings.app_name}  -  {settings.app_description}").dict()
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)


@router.post("/login", description="Business login", response_model=LoginModel)
async def login(request: LoginModel = Body(...)):
    # Check whether user exists.
    user = await users_collection.find_one({"email": request.email})
    if user is None:
        return get_error_response("User not found.", status.HTTP_404_NOT_FOUND)

    user = UserModel.parse_obj(user)
    password_match = verify_password(request.password, user.password)
    if not password_match:
        return get_error_response("Incorrect password",
                                  status.HTTP_404_NOT_FOUND)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={
        "sub":
        user.email,
        "permissions":
        UserActionMatrix.get(user.role)
    },
                                       expires_delta=access_token_expires)
    expiry_time = get_timestamp() + ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 1000
    response = LoginResponseModel(id=str(user.id),
                                  name=user.name,
                                  email=user.email,
                                  access_token=access_token,
                                  access_token_expiry=expiry_time,
                                  role=user.role)
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(response))


@router.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends()):
    user: object = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={
        "sub":
        user.get("email"),
        "permissions":
        UserActionMatrix.get(user["role"])
    },
                                       expires_delta=access_token_expires)
    expiry_time = get_timestamp() + ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 1000
    response = LoginResponseModel(id=str(user["_id"]),
                                  name=user["name"],
                                  email=user["email"],
                                  access_token=access_token,
                                  access_token_expiry=expiry_time,
                                  role=user["role"])
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(response))


@router.post("/complete_registration", description="Business login")
async def signup(request: SignupModel = Body(...)):
    # Check user exists
    user_exists = await users_collection.find_one({"email": request.email})
    if user_exists:
        return get_error_response("Email already exists",
                                  status.HTTP_400_BAD_REQUEST)
    timestamp = get_timestamp()
    hashed_password = get_password_hash(request.password)
    company_id = ObjectId()
    user: UserModel = UserModel(name=request.name,
                                email=request.email,
                                password=hashed_password,
                                phone=request.phone,
                                role=UserRole.business_admin,
                                signed_up_ts=timestamp,
                                updated_ts=timestamp,
                                status="completed")

    await users_collection.insert_one(jsonable_encoder(user))
    return JSONResponse(status_code=status.HTTP_201_CREATED,
                        content=jsonable_encoder(user))


"""
    user: dict = authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    confirm_url = \
        f"{os.environ.get('FOOD_SAFETY_URL')}/login/business"

    email_dict = {
        "email": EmailTemplate.new_account,
  
        "email_from_address": os.environ["CEROED_EMAIL_FROM_ADDRESS"],
        "email_to_address": request.email,
        "user_password": request.password,
        "login_url": confirm_url,
        "subject": "CeroED user registration"
    }
    await send_email_to_user(email_dict)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.get("email")},
                                       expires_delta=access_token_expires)
    expiry_time = get_timestamp() + ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 1000
    response = LoginResponseModel(id=str(user.get("_id")),
                                  name=user.get("name"),
                                  email=user.get("email"),
                                  access_token=access_token,
                                  access_token_expiry=expiry_time,
                                  role=user.get("role"))
    return JSONResponse(status_code=status.HTTP_201_CREATED,
                        content=jsonable_encoder(response))
"""


@router.post("/refresh_token", description="Business refresh token")
async def refresh_token():
    response = APIResponseModel(status=True, message="FOOD SAFETY").dict()
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)


@router.post("/log_out", description="Business logout")
async def log_out():
    response = APIResponseModel(status=True, message="FOOD SAFETY").dict()
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)


""""
@router.post("/forgot_password", description="Forgot password")
async def forgot_password(request: ForgotPasswordModel = Body(...)):
    email = request.email
    otp = str(random_with_n_digits(4))
    user_found = await users_collection.find_one({"email": email, "is_deleted": False, "status": "completed"})
    if user_found:

        update = {
            "otp": otp,
            "otp_expiry": get_timestamp() + OTP_EXPIRE_MINUTES * 60 * 1000,
        }
        await users_collection.update_one({"_id": user_found.get("_id")}, {"$set": update})
        email_dict = {
            "email": EmailTemplate.reset_password,
            "email_from_address": os.environ["FOOD_SAFETY_EMAIL_FROM_ADDRESS"],
            "email_to_address": request.email,
            "otp": otp,
            "subject": "FOOD SAFETY password reset"
        }

        await send_email_to_user(email_dict)
        response = {
            "status": True
        }
        return JSONResponse(status_code=status.HTTP_200_OK, content=response)
    else:
        response = {
            "status": False,
            "message": "Operation not valid , account may be deleted or not have signed in already."
        }
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=response)
"""


@router.post("/reset_password", description="Reset password")
async def reset_password(request: ResetPasswordModel = Body(...)):
    user = await users_collection.find_one({"email": request.email})
    # otp = user.get("otp")
    otp = "5201"
    """
    otp_expiry = int(user.get("otp_expiry"))
    if get_timestamp() > otp_expiry:
        raise HTTPException(status_code=401, detail="Request expired")
    """
    if request.otp == otp:
        new_password = get_password_hash(request.new_password)
        r = await users_collection.update_one(
            {"_id": str(user.get("_id"))},
            {"$set": {
                "password": new_password
            }})
        if r.modified_count == 1:
            response = {
                "status": True,
                "message": "Password changed successfully"
            }

            return JSONResponse(status_code=200, content=response)
        else:
            response = {"status": False, "message": "Password change failed"}
            return JSONResponse(status_code=400, content=response)
    else:
        return get_error_response("Incorrect OTP", status.HTTP_404_NOT_FOUND)


@router.post("/change_password", description="Change password")
async def change_password(request: ChangePasswordModel = Body(...),
                          user: object = Depends(get_current_active_user)):
    user = await users_collection.find_one({"_id": user["_id"]})
    user = UserModel.parse_obj(user)
    if request.current_password == request.new_password:
        return get_error_response(
            "Current password and new passwords cannot be same",
            status.HTTP_500_INTERNAL_SERVER_ERROR)
    password_match = verify_password(request.current_password, user.password)
    if not password_match:
        return get_error_response("Incorrect password",
                                  status.HTTP_500_INTERNAL_SERVER_ERROR)
    new_password = get_password_hash(request.new_password)
    r = await users_collection.update_one({"_id": str(user.id)},
                                          {"$set": {
                                              "password": new_password
                                          }})
    if r.modified_count == 1:
        response = {"status": True, "message": "Password changed successfully"}
        return JSONResponse(status_code=200, content=response)
    else:
        response = {"status": False, "message": "Password change failed"}
        return JSONResponse(status_code=400, content=response)


@router.get("/confirm-email/{user_id}/{code}", description="confirm email")
async def confirm_email(user_id: str, code: str):
    user_result = await users_collection.find_one({
        "_id": user_id,
        "is_deleted": False,
        "activation_code": code
    })

    if user_result is None:
        raise HTTPException(status_code=404, detail="User not found")
    if get_timestamp() > user_result.get("invitation_expiry_time"):
        raise HTTPException(status_code=401, detail="Request expired")
    response = {
        "id": user_result.get("_id"),
        "email": user_result.get("email")
    }
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(response))


@router.post("/set-password", description="Business password reset")
async def set_password(request: SetPasswordLoginModel = Body(...)):
    # Check whether user exists.
    user = await users_collection.find_one({
        "_id": request.user_id,
        "is_deleted": False,
        "activation_code": request.code
    })
    if user is None:
        return get_error_response("User not found.", status.HTTP_404_NOT_FOUND)
    if get_timestamp() > user.get("invitation_expiry_time") or user.get(
            "status") == "completed":
        raise HTTPException(status_code=401, detail="Request expired")

    hashed_password = get_password_hash(request.password)
    update = {
        "password": hashed_password,
        "updated_ts": get_timestamp(),
        "name": request.name,
        "status": "completed"
    }
    r = await users_collection.update_one({"_id": user.get("_id")},
                                          {"$set": update})
    if r.modified_count != 1:
        raise HTTPException(status_code=501,
                            detail="Error occurred during operation")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.get("email")},
                                       expires_delta=access_token_expires)
    expiry_time = get_timestamp() + ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 1000
    response = LoginResponseModel(id=str(user.get("_id")),
                                  name=request.name,
                                  email=user.get("email"),
                                  access_token=access_token,
                                  access_token_expiry=expiry_time,
                                  role=user.get("role"))
    return JSONResponse(status_code=status.HTTP_200_OK,
                        content=jsonable_encoder(response))


def random_with_n_digits(n):
    range_start = 10**(n - 1)
    range_end = (10**n) - 1
    return randint(range_start, range_end)


"""
async def send_email_to_user(email_dict: object):
    email_from_address = email_dict.get("email_from_address")
    email_to_address = email_dict.get("email_to_address")
    subject = email_dict.get("subject")
    if EmailTemplate.new_account == email_dict.get("email"):
        template = await get_email_template(EmailTemplate.new_account, email_dict)
    elif EmailTemplate.reset_password == email_dict.get("email"):
        template = await get_email_template(EmailTemplate.reset_password, email_dict)
    mail_request = MailRequest(
        from_email=email_from_address,
        to_emails=email_to_address,
        subject=subject,
        html_content=template.body)
    send_email(mail_request)
"""

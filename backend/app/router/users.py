from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr, BaseModel, Field
from starlette import status
from starlette.responses import JSONResponse

from app.db.base import users_collection, roles_collection
from app.models.base import PyObjectId
from app.models.user import InviteUpdateModel, InviteUserModel, UserRole
from app.router.auth import get_user, get_current_active_user
from app.utils.utils import APIResponseModel, get_error_response, get_timestamp

router = APIRouter(
    prefix="/business/users",
    tags=["users"],
    responses={404: {
        "description": "Not found"
    }},
)
ACCESS_TOKEN_EXPIRE_MINUTES = 2880


class AddUserModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    firstname: str
    lastname: str
    email: EmailStr = Field(...)
    role: str = Field(...)
    is_invited: bool = False

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "firstname": "name",
                "lastname": "last_name",
                "email": "jdoe@example.com",
                "role": "database-user",
            }
        }


@router.get("/list-role")
async def list_role(user: object = Depends(get_current_active_user)):
    roles = await roles_collection.find().to_list(100)
    roles = [{"role": x.get("role")} for x in roles]
    return roles


@router.get("", description="List all users")
async def list_users(user: object = Depends(get_current_active_user)):
    company_id = user.get("company_id")
    associated_users = await users_collection.find({
        "is_deleted": False
    }).to_list(1000)
    response = []

    for user in associated_users:
        logged_in_status = get_user_logged_in_status(user)
        result = {
            "id": user.get("_id"),
            "name": user.get("name"),
            "email": user.get("email"),
            "role": user.get("role"),
            "logged_in": logged_in_status,
        }
        response.append(result)
    return response


@router.get("/{user_id}", description="Get user")
async def get_users(user_id: str,
                    user: object = Depends(get_current_active_user)):
    user_result = await users_collection.find_one({
        "_id": user_id,
        "is_deleted": False
    })
    if user_result is None:
        raise HTTPException(status_code=404, detail="User not found")

    logged_in_status = get_user_logged_in_status(user_result)
    response = {
        "id": user_result.get("_id"),
        "firstname": user_result.get("first_name"),
        "lastname": user_result.get("last_name"),
        "email": user_result.get("email"),
        "role": user_result.get("role"),
        "logged_in": logged_in_status
    }

    return response


@router.post("", description="Add a user")
async def add_user(request: AddUserModel = Body(...),
                   user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.super_admin:
        return get_error_response("Invalid operation.",
                                  status.HTTP_401_UNAUTHORIZED)
    user_found: object = get_user(request.email)
    if not user_found:
        activation_code = str(ObjectId())
        timestamp = get_timestamp()
        invited_user: InviteUserModel = InviteUserModel(
            name=request.firstname + ' ' + request.lastname,
            email=request.email,
            role=request.role,
            invited_id=user["_id"],
            invitation_expiry_time=get_timestamp() +
            ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 1000,
            activation_code=activation_code,
            status="pending",
            signed_up_ts=timestamp,
            is_invited=True)
        await users_collection.insert_one(jsonable_encoder(invited_user))
        response = APIResponseModel(status=True, message="added").dict()
        """
        inserted_user = get_user(invited_user.email)
        confirm_url = \
            f"{os.environ.get('CEROED_LOGIN_URL')}/login/business/{inserted_user.get('_id')}/" \
            f"{inserted_user.get('activation_code')}"

        email_dict = {
            "company_logo": company.get("logo_url"),
            "email_from_address": os.environ["CEROED_EMAIL_FROM_ADDRESS"],
            "email_to_address": request.email,
            "application_name": "CeroED",
            "company_name": company.get("name"),
            "confirm_url": confirm_url,
            "subject": "CeroED user invitation"
        }

        await send_email_to_user(email_dict)
        return response
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already invited")
       """
        return response


"""
@router.post("/resend-activation-link/{user_id}")
async def resend_activation_link(user_id: str, user: object = Depends(get_current_active_user)):
   
    #Resend activation link to user so that they can reset their password and login.
    #This method need to be called only for instances of users whose logged_in status = Invited , refer list users api
   
    if user.get("role") not in UserActionMatrix.get(UserActionType.user_invite):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized method access.")
    user_found = await users_collection.find_one(
        {"_id": user_id, "is_deleted": False, "status": "pending", "is_invited": True,
         "company_id": user.get("company_id")})
    if user_found is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found.")
    activation_code = str(ObjectId())
    timestamp = get_timestamp()
    update = {
        "activation_code": activation_code,
        "invitation_expiry_time": get_timestamp() + ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 1000,
        "signed_up_ts": timestamp
    }
    await users_collection.update_one({"_id": user_id}, {"$set": update})
    response = APIResponseModel(status=True, message="updated").dict()
    inserted_user = await users_collection.find_one(
        {"_id": user_id, "is_deleted": False, "company_id": user.get("company_id")})
    company = await companies_collection.find_one({"_id": str(user.get("company_id"))})
    confirm_url = \
        f"{os.environ.get('CEROED_LOGIN_URL')}/login/business/{inserted_user.get('_id')}/" \
        f"{inserted_user.get('activation_code')}"

    email_dict = {
        "company_logo": company.get("logo_url"),
        "email_from_address": os.environ["CEROED_EMAIL_FROM_ADDRESS"],
        "email_to_address": inserted_user.get('email'),
        "application_name": "CeroED",
        "company_name": company.get("name"),
        "confirm_url": confirm_url,
        "subject": "CeroED user resend invitation"
    }

    await send_email_to_user(email_dict)
    return response
"""


@router.put("/{user_id}", description="Update a user")
async def update_user(user_id: str,
                      request: InviteUpdateModel = Body(...),
                      user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.super_admin:
        return get_error_response("Invalid operation.",
                                  status.HTTP_401_UNAUTHORIZED)
    user_found: object = get_user(request.email)
    invited_user = await users_collection.find_one({
        "_id": user_id,
        "is_deleted": False
    })

    if invited_user:
        if invited_user.get("email") != request.email:
            if not user_found:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content="Bad request")
        update = {
            "first_name": request.firstname,
            "last_name": request.lastname,
            "role": request.role,
            "updated_ts": get_timestamp(),
        }

        await users_collection.update_one({"_id": user_id}, {"$set": update})
        response = APIResponseModel(status=True, message="updated").dict()
        return JSONResponse(status_code=status.HTTP_200_OK, content=response)
    else:
        response = "user not found"
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content=response)


@router.delete("/{user_id}", description='Delete user')
async def delete_user(user_id: str,
                      user: object = Depends(get_current_active_user)):
    """
    Delete a user
    """
    user_found = await users_collection.find_one({
        "_id": user_id,
        "is_deleted": False
    })
    if user.get('role') != UserRole.super_admin:
        return get_error_response("Invalid operation.",
                                  status.HTTP_401_UNAUTHORIZED)
    if user_found is None:
        return get_error_response("User not found.", status.HTTP_404_NOT_FOUND)
    if user.get('_id') == user_id:
        return get_error_response("Invalid operation.",
                                  status.HTTP_401_UNAUTHORIZED)
    update = {"is_deleted": True}
    await users_collection.update_one({"_id": str(user_id)}, {"$set": update})
    response = APIResponseModel(status=True, message="Deleted").dict()
    return JSONResponse(status_code=status.HTTP_200_OK, content=response)


"""
async def send_email_to_user(email_dict: object):
    email_from_address = email_dict.get("email_from_address")
    email_to_address = email_dict.get("email_to_address")
    subject = email_dict.get("subject")
    template = await get_email_template(EmailTemplate.add_user, email_dict)
    mail_request = MailRequest(
        from_email=email_from_address,
        to_emails=email_to_address,
        subject=subject,
        html_content=template.body)

    send_email(mail_request)
"""


def get_user_logged_in_status(user_result):
    if user_result.get("is_invited") and user_result.get(
            "status") == "pending":
        logged_in = "Invited"
    elif user_result.get("status") == "completed":
        logged_in = "Active"
    else:
        logged_in = "Unknown"
    return logged_in

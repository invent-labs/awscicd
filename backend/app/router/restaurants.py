import base64
import os
from typing import Optional

import pymongo
from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr, BaseModel, Field
from starlette import status
from starlette.responses import JSONResponse

from app.db.base import users_collection, restaurants_collection, circles_collection, districts_collection, \
    restaurants_type_collection
from app.models.base import PyObjectId
from app.models.restaurants import RestaurantsModel, AddRestaurants, Location, UpdateRestaurants, RestaurantType
from app.models.user import UserRole
from app.router.auth import get_current_active_user
from app.utils.utils import get_error_response, get_timestamp

router = APIRouter(
    prefix="/business",
    tags=["restaurants"],
    responses={404: {
        "description": "Not found"
    }},
)


@router.post("/restaurants/")
async def create_restaurants(request: AddRestaurants, user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.business_admin:
        return get_error_response("Invalid operation.", status.HTTP_401_UNAUTHORIZED)
    timestamp = get_timestamp()
    coordinates = []
    coordinates.extend([request.latitude, request.longitude])
    location = Location(
        type="point",
        coordinates=coordinates
    )
    district = await districts_collection.find_one({"_id": ObjectId(request.district)})
    if request.is_new_logo:
        logo = request.logo.split(',')
        contents = base64.b64decode(logo[1])
        logo_name = ObjectId()
        destination_file_path = "static/logo/" + str(logo_name) + ".png"
        logo_url = 'http://127.0.0.1:8000/static/logo/'
        with open(destination_file_path, 'wb') as f:
            f.write(contents)
        logo = os.path.join(logo_url, str(logo_name) + ".png")
    restaurant = RestaurantsModel(
        name=request.name,
        district_id=request.district,
        district=district.get("name"),
        description=request.description,
        circle=request.circle,
        location=location,
        type=request.type,
        logo=logo,
        rating=float(request.rating),
        status="open",
        created_by=user.get("_id"),
        created_by_name=user.get("name"),
        created_ts=timestamp
    )
    await restaurants_collection.insert_one(jsonable_encoder(restaurant))
    response = {
        "id": str(restaurant.id)
    }
    return response


@router.post("/restaurants/upload-image")
async def upload_image(restaurant_id: str, file: UploadFile, user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.business_admin:
        return get_error_response("Invalid operation.", status.HTTP_401_UNAUTHORIZED)
    restaurant = await restaurants_collection.find_one({
        "_id": restaurant_id,
        "is_deleted": False
    })
    if restaurant is None:
        return get_error_response("Not Found.", status.HTTP_404_NOT_FOUND)
    contents = await file.read()
    destination_file_path = "static/restaurants-photos/" + file.filename
    base_url = 'http://127.0.0.1:8000/static/restaurants-photos/'
    with open(destination_file_path, 'wb') as f:
        f.write(contents)

    update = {
        "image": {"id": ObjectId(),
                  "image": os.path.join(base_url, file.filename),
                  "is_deleted": False}
    }
    await restaurants_collection.update_one({"_id": restaurant_id}, {"$push": update})
    response = {
        "id": restaurant_id,
        "status": True,
        "message": "uploaded"
    }
    return response


@router.get("/restaurants")
async def list_restaurants(restaurant_type: Optional[RestaurantType] = None,
                           skip: int = 0,
                           limit: int = 40,
                           user: object = Depends(get_current_active_user),
                           query: str = None, district: str = None,
                           circle: str = None
                           ):
    await restaurants_collection.create_index([('name', pymongo.TEXT)], default_language='english')
    if user.get('role') != UserRole.business_admin:
        return get_error_response("Invalid operation.", status.HTTP_401_UNAUTHORIZED)
    find_query = {
        "is_deleted": False,
    }
    if district is not None:
        find_query["district"] = {"$regex": district, "$options": "i"}
    if restaurant_type is not None:
        find_query["type"] = restaurant_type

    if query is not None:
        find_query["$text"] = {"$search": query}
    if circle is not None:
        find_query["circle"] = circle
    restaurants = await restaurants_collection.find(find_query).skip(skip).limit(
        limit).to_list(limit)
    restaurants_response = [RestaurantsModel(**x).list_response() for x in restaurants]
    return restaurants_response


@router.delete("/restaurants/delete-image")
async def delete_images(restaurant_id: str, image_id: str, user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.business_admin:
        return get_error_response("Invalid operation.", status.HTTP_401_UNAUTHORIZED)
    restaurant = await restaurants_collection.find_one({
        "_id": restaurant_id,
        "is_deleted": False
    })
    if restaurant is None:
        return get_error_response("Not Found.", status.HTTP_404_NOT_FOUND)
    update = {
        "image.$.is_deleted": True
    }
    await restaurants_collection.update_one({"_id": restaurant_id, "image.id": ObjectId(image_id)}, {"$set": update})
    response = {
        "id": restaurant_id,
        "status": True,
        "message": "deleted"
    }
    return response


@router.get("/restaurants/{restaurants_id}", description="Get restaurant data")
async def get_restaurants(
        restaurants_id: str,
        user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.business_admin:
        return get_error_response("Invalid operation.", status.HTTP_401_UNAUTHORIZED)
    restaurant = await restaurants_collection.find_one({
        "_id": restaurants_id,
        "is_deleted": False
    })
    restaurants_response = RestaurantsModel(**restaurant).detailed_response()
    return restaurants_response


@router.put('/restaurants/{restaurant_id}')
async def update_restaurant(restaurant_id: str, request: UpdateRestaurants,
                            user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.business_admin:
        return get_error_response("Invalid operation.", status.HTTP_401_UNAUTHORIZED)

    restaurant = await restaurants_collection.find_one({
        "_id": restaurant_id,
        "is_deleted": False
    })
    district = await districts_collection.find_one({"_id": ObjectId(request.district)})
    if restaurant is None:
        return get_error_response("Not Found.", status.HTTP_404_NOT_FOUND)
    restaurant = RestaurantsModel(**restaurant)
    coordinates = []
    coordinates.extend([request.latitude, request.longitude])
    location = Location(
        type="point",
        coordinates=coordinates
    )
    if request.is_new_logo:
        logo = request.logo.split(',')
        contents = base64.b64decode(logo[1])
        logo_name = ObjectId()
        destination_file_path = "static/logo/" + str(logo_name) + ".png"
        logo_url = 'http://127.0.0.1:8000/static/logo/'
        with open(destination_file_path, 'wb') as f:
            f.write(contents)
        logo = os.path.join(logo_url, str(logo_name) + ".png")
    else:
        logo = request.logo
    images = []
    if len(request.images) != 0:
        for image in request.images:
            image_str = image.split(',')
            contents = base64.b64decode(image_str[1])
            image_name = ObjectId()
            destination_file_path = "static/restaurants-photos/" + str(image_name) + ".png"
            image_url = 'http://127.0.0.1:8000/restaurants-photos/'
            with open(destination_file_path, 'wb') as f:
                f.write(contents)
            update = {
                "image": {"id": ObjectId(),
                          "image": os.path.join(image_url, str(image_name) + ".png"),
                          "is_deleted": False}
            }
            images.append(update)

    timestamp = get_timestamp()
    restaurant.name = request.name
    restaurant.district_id = request.district
    restaurant.district = district.get("name")
    restaurant.description = request.description
    restaurant.circle = request.circle
    restaurant.location = location
    restaurant.logo = logo
    restaurant.image=images
    restaurant.rating = float(request.rating)
    restaurant.last_updated_ts = timestamp
    restaurant.updated_by = user.get("_id")
    restaurant.updated_by_name = user.get("name")

    await restaurants_collection.update_one({"_id": restaurant_id}, {"$set": jsonable_encoder(restaurant)})
    response = {
        "id": restaurant_id,
        "message": "updated"
    }
    return response


@router.delete("/restaurants/{restaurant_id}")
async def delete_restaurant(restaurant_id: str, user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.business_admin:
        return get_error_response("Invalid operation.", status.HTTP_401_UNAUTHORIZED)
    restaurant = await restaurants_collection.find_one({
        "_id": restaurant_id,
        "is_deleted": False
    })
    if restaurant is None:
        return get_error_response("Not Found.", status.HTTP_404_NOT_FOUND)
    update = {
        "is_deleted": True
    }
    await restaurants_collection.update_one({"_id": restaurant_id}, {"$set": update})
    response = {
        "id": restaurant_id,
        "status": True,
        "message": "deleted"
    }
    return response


@router.get("/restaurants/restaurant_type")
async def get_restaurant_type(user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.business_admin:
        return get_error_response("Invalid operation.", status.HTTP_401_UNAUTHORIZED)
    restaurants_type = await restaurants_type_collection.find().to_list(100)
    return restaurants_type


@router.get("/district/circles")
async def list_circle(user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.business_admin:
        return get_error_response("Invalid operation.", status.HTTP_401_UNAUTHORIZED)
    circles = await circles_collection.find({"is_deleted": False}).to_list(200)
    circle_list = [{"name": x.get("name"), "district": x.get("district")} for x in circles]
    return circle_list


@router.get("/district")
async def list_district(user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.business_admin:
        return get_error_response("Invalid operation.", status.HTTP_401_UNAUTHORIZED)
    district = await districts_collection.find().to_list(200)
    district_list = [{"id": str(x.get("_id")), "name": x.get("name")} for x in district]
    return district_list


@router.get("/restaurant_type")
async def get_restaurant_type(user: object = Depends(get_current_active_user)):
    if user.get('role') != UserRole.business_admin:
        return get_error_response("Invalid operation.", status.HTTP_401_UNAUTHORIZED)
    restaurants_type = await restaurants_type_collection.find().to_list(100)
    restaurants_type_list = [{"id": str(x.get("_id")), "name": x.get("name").capitalize()} for x in restaurants_type]
    return restaurants_type_list

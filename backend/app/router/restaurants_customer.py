import os
from typing import Optional

import pymongo
from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr, BaseModel, Field
from starlette import status
from starlette.responses import JSONResponse

from app.db.base import users_collection, restaurants_collection, restaurants_type_collection, districts_collection, \
    circles_collection
from app.models.base import PyObjectId
from app.models.restaurants import RestaurantsModel, AddRestaurants, Location, UpdateRestaurants, RestaurantType
from app.models.user import UserRole
from app.router.auth import get_current_active_user
from app.utils.utils import get_error_response, get_timestamp

router = APIRouter(
    tags=["restaurants-customer"],
    responses={404: {
        "description": "Not found"
    }},
)


@router.get("/restaurants/restaurant_type")
async def get_restaurant_type():
    restaurants_type = await restaurants_type_collection.find().to_list(100)
    restaurants_type_list = [{
        "id": str(x.get("_id")),
        "name": x.get("name").capitalize()
    } for x in restaurants_type]
    return restaurants_type_list


@router.get("/restaurants/")
async def list_restaurants(restaurant_type: Optional[RestaurantType] = None,
                           skip: int = 0,
                           limit: int = 40,
                           lat: float = None,
                           lon: float = None,
                           query: str = None,
                           district: str = None,
                           circle: str = None,
                           rating: int = None):
    await restaurants_collection.create_index([('name', pymongo.TEXT)],
                                              default_language='english')
    find_query = {
        "is_deleted": False,
    }
    if restaurant_type is not None:
        find_query["type"] = restaurant_type
    if query is not None:
        find_query["$text"] = {"$search": query}
    if district is not None:
        find_query["district"] = {"$regex": district, "$options": "i"}
    if circle is not None:
        find_query["circle"] = circle
    if rating is not None:
        find_query["rating"] = rating
    
    # @todo add geospacial query here.
    restaurants = await restaurants_collection.find(find_query).skip(
        skip).limit(limit).to_list(limit)
    restaurants_response = [
        RestaurantsModel(**x).list_response() for x in restaurants
    ]
    return restaurants_response


@router.get("/restaurants/{restaurant_id}", description="Get emission data")
async def get_restaurants(restaurant_id: str):
    restaurant = await restaurants_collection.find_one({
        "_id": restaurant_id,
        "is_deleted": False,
    })
    restaurants_response = RestaurantsModel(**restaurant).detailed_response()
    return restaurants_response


@router.get("/district")
async def list_district():
    district = await districts_collection.find().to_list(200)
    district_list = [{
        "id": str(x.get("_id")),
        "name": x.get("name")
    } for x in district]
    return district_list


@router.get("/district/circles")
async def list_circle():
    circles = await circles_collection.find({"is_deleted": False}).to_list(200)
    circle_list = [{
        "name": x.get("name"),
        "district": x.get("district")
    } for x in circles]
    return circle_list

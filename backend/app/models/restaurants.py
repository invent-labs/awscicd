from enum import Enum
from typing import Optional, List

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field

from app.db.base import districts_collection_pymongo
from app.models.base import PyObjectId


class RestaurantsModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    location: dict
    description: str
    type: str
    circle: Optional[str] = None
    district_id: str
    district: str
    status: str
    logo: str
    image: List[Optional[dict]] = []
    rating: Optional[int] = None
    created_ts: int
    last_updated_ts: Optional[int] = None
    created_by: PyObjectId
    created_by_name: str
    updated_by: Optional[PyObjectId] = None
    updated_by_name: Optional[str] = None
    is_deleted: bool = False

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    def list_response(self):
        return {
            "id":
            str(self.id),
            "name":
            self.name,
            "type":
            self.type,
            "district":
            self.district,
            "circle":
            self.circle,
            "logo":
            self.logo,
            "status":
            self.status,
            "rating":
            self.rating,
            "images": [{
                "id": str(x.get("id")),
                "image": x.get("image")
            } for x in self.image if x.get("is_deleted") == False],
            "created_ts":
            self.created_ts,
            "created_by":
            self.created_by_name,
        }

    def detailed_response(self):
        return {
            "id":
            str(self.id),
            "name":
            self.name,
            "latitude":
            float(self.location["coordinates"][0]),
            "longitude":
            float(self.location["coordinates"][1]),
            "district_id":
            self.district_id,
            "logo":
            self.logo,
            "district":
            self.district,
            "type":
            self.type,
            "circle":
            self.circle,
            "status":
            self.status,
            "images": [{
                "id": str(x.get("id")),
                "image": x.get("image")
            } for x in self.image if x.get("is_deleted") == False],
            "description":
            self.description,
            "rating":
            self.rating,
            "created_ts":
            self.created_ts,
            "created_by":
            self.created_by_name,
            "last_updated_ts":
            self.last_updated_ts,
            "updated_by":
            self.updated_by_name,
        }


class AddRestaurants(BaseModel):
    name: str
    district: str
    type: str
    description: Optional[str] = None
    circle: Optional[str] = None
    latitude: Optional[float] = 0
    longitude: Optional[float] = 0
    rating: Optional[int] = 0
    logo: str
    is_new_logo: bool

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "restaurant_name",
                "district": "trivandrum",
                "description": "description",
                "type": "dining",
                "circle": "string",
                "latitude": 0,
                "longitude": 0,
                "rating": 0,
                "logo": "str",
                "is_new_logo": "true"
            }
        }


class UpdateRestaurants(BaseModel):
    name: str
    district: str
    type: str
    description: Optional[str] = None
    circle: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[str] = None
    restaurant_image: Optional[str] = None
    logo: str
    images: Optional[List] = None
    is_new_logo: bool

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "restaurant_name",
                "district": "trivandrum",
                "description": "description",
                "type": "dining",
                "circle": "string",
                "latitude": 0,
                "longitude": 0,
                "rating": 0,
                "logo": "str",
                "is_new_logo": "true",
                "images": []
            }
        }


class Location(BaseModel):
    type: str
    coordinates: Optional[List[float]]


class RestaurantType(str, Enum):
    bakery = "bakery"
    juicery = "juicery"
    restaurant = "restaurant"

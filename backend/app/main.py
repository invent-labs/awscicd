import logging
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from fastapi.staticfiles import StaticFiles

from app.router import auth, users, restaurants, restaurants_customer
from mangum import Mangum

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

app = FastAPI()
# app.mount("/static", StaticFiles(directory="static"), name="static")
origins = [
    "http://whitelist.com",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(restaurants.router)
app.include_router(restaurants_customer.router)


# to make it work with Amcd app && uvicorn main:app --reloadazon Lambda, we create a handler object
handler = Mangum(app=app)

#if __name__ == '__main__':
#    uvicorn.run(app=app, host='localhost', port=8000)

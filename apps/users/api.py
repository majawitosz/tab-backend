from ninja import NinjaAPI, Schema
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_extra import NinjaExtraAPI
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from ninja.errors import HttpError


api = NinjaExtraAPI()
api.register_controllers(NinjaJWTDefaultController)


class RegisterSchema(Schema):
    username: str
    password: str
    email: str

class UserSchema(Schema):
    username: str
    email: str
    is_authenticated: bool

@api.get("/me", response=UserSchema, auth=JWTAuth())
def me(request):
    return request.user

@api.post("/register")
def register(request, data: RegisterSchema):
 
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username already exists")
    
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email already exists")

    user = User(
        username=data.username,
        email=data.email,
        password=make_password(data.password)  
    )
    user.save()

    return {
        "username": user.username,
        "email": user.email,
        "is_authenticated": user.is_authenticated
    }
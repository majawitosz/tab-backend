# apps/dania/api.py
from typing import List, Optional, Literal

from django.shortcuts import get_object_or_404
from ninja import Schema
from ninja.errors import HttpError
from ninja_extra import NinjaExtraAPI
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController

from .models import Allergen, MenuItem

api = NinjaExtraAPI()
# rejestrujemy endpoints do logowania / tokenów
api.register_controllers(NinjaJWTDefaultController)  




class AllergenIn(Schema):
    name: str
    description: Optional[str] = None

class AllergenOut(Schema):
    id: int
    name: str
    description: Optional[str]

class MenuItemIn(Schema):
    name: str
    description: Optional[str] = None
    price: float
    category: str
    is_available: bool = True
    is_visible: bool = True
    image_url: Optional[str] = None
    allergen_ids: Optional[List[int]] = []  # relacja M2M

class MenuItemOut(Schema):
    id: int
    name: str
    description: Optional[str]
    price: float
    category: str
    is_available: bool
    is_visible: bool
    image_url: Optional[str]
    allergens: List[AllergenOut]  # zagnieżdżone



@api.get("/alergeny", response=List[AllergenOut])
def list_allergens(
    request,
    sort_by: Literal["id", "name"] = "id"
):
    qs = Allergen.objects.all().order_by(sort_by)
    return qs


@api.get("/alergeny/{allergen_id}", response=AllergenOut)
def get_allergen(request, allergen_id: int):
    return get_object_or_404(Allergen, id=allergen_id)


@api.post("/alergeny", response=AllergenOut, auth=JWTAuth())
def create_allergen(request, data: AllergenIn):
    if Allergen.objects.filter(name=data.name).exists():
        raise HttpError(400, "Alergen o tej nazwie już istnieje")
    obj = Allergen.objects.create(**data.dict())
    return obj

@api.put("/alergeny/{allergen_id}", response=AllergenOut, auth=JWTAuth())
def update_allergen(request, allergen_id: int, data: AllergenIn):
    obj = get_object_or_404(Allergen, id=allergen_id)
    for k, v in data.dict().items():
        setattr(obj, k, v)
    obj.save()
    return obj

@api.delete("/alergeny/{allergen_id}", auth=JWTAuth())
def delete_allergen(request, allergen_id: int):
    obj = get_object_or_404(Allergen, id=allergen_id)
    obj.delete()
    return {"ok": True}


# ─── DANIA (MENU ITEMS) ──────────────────────────────────────────────

@api.get("/dania", response=List[MenuItemOut])
def list_menuitems(
    request,
    category: Optional[str]   = None,
    max_price: Optional[float] = None,
):
    qs = MenuItem.objects.filter(is_visible=True)
    if category:
        qs = qs.filter(category=category)
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)
    return qs

@api.get("/dania/{item_id}", response=MenuItemOut)
def get_menuitem(request, item_id: int):
    return get_object_or_404(MenuItem, id=item_id, is_visible=True)

@api.post("/dania", response=MenuItemOut, auth=JWTAuth())
def create_menuitem(request, data: MenuItemIn):
    item = MenuItem.objects.create(
        name=data.name,
        description=data.description,
        price=data.price,
        category=data.category,
        is_available=data.is_available,
        is_visible=data.is_visible,
        image_url=data.image_url,
    )
    if data.allergen_ids:
        item.allergens.set(data.allergen_ids)
    return item

@api.put("/dania/{item_id}", response=MenuItemOut, auth=JWTAuth())
def update_menuitem(request, item_id: int, data: MenuItemIn):
    item = get_object_or_404(MenuItem, id=item_id)
    payload = data.dict(exclude_unset=True)
    ids = payload.pop("allergen_ids", None)
    for k, v in payload.items():
        setattr(item, k, v)
    item.save()
    if ids is not None:
        item.allergens.set(ids)
    return item

@api.delete("/dania/{item_id}", auth=JWTAuth())
def delete_menuitem(request, item_id: int):
    item = get_object_or_404(MenuItem, id=item_id)
    item.delete()
    return {"ok": True}
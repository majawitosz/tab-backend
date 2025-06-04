# apps/dania/api.py
import os
from datetime import datetime
from typing import List, Optional, Literal
from uuid import uuid4

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import Schema, File, Form
from ninja import Body
from ninja.errors import HttpError
from ninja_extra import NinjaExtraAPI
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja.files import UploadedFile

from .models import Allergen, MenuItem, Order, OrderItem

api = NinjaExtraAPI(
    version="1.0.0",         # unikalna wersja dla dania
    urls_namespace="dania"   # unikalna przestrzeń nazw
)

# rejestrujemy endpoints do logowania / tokenów
api.register_controllers(NinjaJWTDefaultController)  

UPLOAD_DIR = os.path.join(settings.BASE_DIR, "media")
os.makedirs(UPLOAD_DIR, exist_ok=True)


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

class DishIn(Schema):
    id: int
    quantity: int

class OrderIn(Schema):
    tableId: int
    totalPrice: float
    createdAt: datetime
    estimatedTime: int
    notes: Optional[str] = ""
    dishes: List[DishIn]

class OrderItemOut(Schema):
    menu_item_id: int
    name: str
    quantity: int
    price_at_time: float

class OrderOut(Schema):
    id: int
    table_number: int
    status: str
    total_amount: float
    estimated_time: int
    created_at: str
    completed_at: Optional[str]
    notes: Optional[str]
    items: List[OrderItemOut]


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
def create_menuitem(
    request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(...),
    category: str = Form(...),
    is_available: bool = Form(True),
    is_visible: bool = Form(True),
    allergen_ids: List[int] = Form(default=[]),      # <-- teraz lista intów
    image: Optional[UploadedFile] = File(None)
):
    image_url = None
    if image:
        if not image.content_type.startswith("image/"):
            raise HttpError(400, "Invalid file type")
        ext = os.path.splitext(image.name)[1]
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb+") as dest:
            for chunk in image.chunks():
                dest.write(chunk)
        image_url = f"/media/{filename}"

    # Tworzymy obiekt bez dodatkowego parsowania
    item = MenuItem.objects.create(
        name=name,
        description=description,
        price=price,
        category=category,
        is_available=is_available,
        is_visible=is_visible,
        image_url=image_url,
    )
    print(allergen_ids)
    if allergen_ids:
        item.allergens.set(allergen_ids)
    print(allergen_ids)
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

@api.post("/orders", auth=JWTAuth())
def create_order(request, data: OrderIn = Body(...)):
    if not data.dishes:
        raise HttpError(400, "Zamówienie musi zawierać co najmniej jedno danie")

    order_items_data = []

    for dish in data.dishes:
        menu_item = get_object_or_404(MenuItem, id=dish.id, is_visible=True)
        order_items_data.append({
            "menu_item": menu_item,
            "quantity": dish.quantity,
            "price_at_time": menu_item.price
        })

    order = Order.objects.create(
        user=request.user,
        table_number=data.tableId,
        status="Active",
        total_amount=data.totalPrice,
        estimated_time=data.estimatedTime,
        notes=data.notes or ""

    )

    for item in order_items_data:
        OrderItem.objects.create(
            order=order,
            menu_item=item["menu_item"],
            quantity=item["quantity"],
            price_at_time=item["price_at_time"]
        )

    return {"order_id": order.id}

@api.get("/orders", response=List[OrderOut], auth=JWTAuth())
def list_orders(request):
    orders = Order.objects.prefetch_related("items__menu_item").all()
    result = []

    for order in orders:
        items = [
            OrderItemOut(
                menu_item_id=item.menu_item.id,
                name=item.menu_item.name,
                quantity=item.quantity,
                price_at_time=float(item.price_at_time),
            )
            for item in order.items.all()
        ]


        result.append(OrderOut(
            id=order.id,
            table_number=order.table_number,
            status=order.status,
            total_amount=float(order.total_amount),
            estimated_time=order.estimated_time,
            created_at=order.created_at.isoformat(),
            completed_at=order.completed_at.isoformat() if order.completed_at else None,
            notes=order.notes,
            items=items
        ))

    return result

@api.post("/orders/{orderId}/status", response=OrderOut, auth=JWTAuth())
def archive_order(request, orderId: int):
    try:
        order = Order.objects.get(id=orderId)
        order.status = "Completed"
        order.completed_at = datetime.now()
        order.save()

        items = [
            OrderItemOut(
                menu_item_id=item.menu_item.id,
                name=item.menu_item.name,
                quantity=item.quantity,
                price_at_time=float(item.price_at_time),
            )
            for item in order.items.all()
        ]

        return OrderOut(
            id=order.id,
            table_number=order.table_number,
            status=order.status,
            total_amount=float(order.total_amount),
            estimated_time=order.estimated_time,
            created_at=order.created_at.isoformat(),
            completed_at=order.completed_at.isoformat() if order.completed_at else None,
            notes=order.notes,
            items=items
        )
    except Order.DoesNotExist:
        raise HttpError(404, "Order not found")


@api.post(
    "/dania/{item_id}/hide",
    response=MenuItemOut,
    auth=JWTAuth(),
    summary="Ukryj pozycję menu"
)
def hide_menuitem(request, item_id: int):

    item = get_object_or_404(MenuItem, id=item_id)
    if not item.is_visible:
        raise HttpError(400, "Menu item is already hidden")
    item.is_visible = False
    item.save(update_fields=["is_visible"])
    return item

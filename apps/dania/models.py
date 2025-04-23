from django.db import models
from django.conf import settings

class Allergen(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    is_available = models.BooleanField(default=True)
    is_visible = models.BooleanField(default=True)
    image_url = models.URLField(blank=True)

    # M2M pośredniczący przez MenuItemAllergen
    allergens = models.ManyToManyField(
        Allergen,
        through='MenuItemAllergen',
        related_name='menu_items'
    )

    def __str__(self):
        return self.name


class MenuItemAllergen(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    allergen = models.ForeignKey(Allergen, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('menu_item', 'allergen')


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    table_number = models.IntegerField()
    status = models.CharField(max_length=50)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_time = models.IntegerField(help_text="w minutach")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Order #{self.id} – {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name='+'
    )
    quantity = models.IntegerField()
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.quantity}× {self.menu_item.name}"

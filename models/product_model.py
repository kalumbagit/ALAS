# app/models/product_model.py
from tortoise import fields
from models.base_model import BaseModel
from models.enum import CurrencyEnum

class Product(BaseModel):
    name = fields.CharField(max_length=150, index=True)  # Ajout index
    description = fields.TextField(null=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = fields.DecimalField(  # Prix barré pour les promos
        max_digits=10, decimal_places=2, null=True
    )
    image_urls = fields.JSONField(default=list)  # Multiple images au lieu d'une seule
    is_available = fields.BooleanField(default=True)
    preparation_time = fields.IntField(null=True)  # en minutes
    stock_quantity = fields.IntField(default=0)
    low_stock_threshold = fields.IntField(default=5)  # Seuil d'alerte stock faible
    attributes = fields.JSONField(default=dict)  # Default dict au lieu de null
    sku = fields.CharField(max_length=100, null=True, unique=True)  # Référence unique
    tags = fields.JSONField(default=list)  # Tags pour recherche/filtrage

    # Audit
    user = fields.UUIDField(index=True)  # Ajout index

    # 🪙 Devise
    currency = fields.CharEnumField(
        CurrencyEnum, default=CurrencyEnum.XAF
    )

    # Relations
    category: fields.ForeignKeyNullableRelation["Category"] = fields.ForeignKeyField(
        "models.Category", 
        related_name="products", 
        null=True, 
        on_delete=fields.SET_NULL,
        index=True  # Ajout index
    )

    class Meta:
        table = "products"
        indexes = [
            ("name", "is_active"),  # Index composite
            ("user", "created_at"),  # Pour les dashboards marchands
        ]

    def __str__(self):
        return f"Product({self.name}, {self.price} {self.currency})"

    @property
    def is_low_stock(self) -> bool:
        """Alerte stock faible"""
        return self.stock_quantity <= self.low_stock_threshold

    @property
    def has_discount(self) -> bool:
        """Vérifie si le produit est en promo"""
        return self.compare_at_price is not None and self.compare_at_price > self.price
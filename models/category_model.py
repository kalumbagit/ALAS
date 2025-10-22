# app/models/category_model.py
from tortoise import fields
from models.base_model import BaseModel

class Category(BaseModel):
    name = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)
    icon_url = fields.CharField(max_length=255, null=True)
    
    # Remplacer is_active par celui de BaseModel
    # is_active = fields.BooleanField(default=True)  # Supprimé car hérité

    # Catégorie globale (null = catégorie publique)
    merchant_id = fields.UUIDField(null=True, index=True)  # Ajout index

    # Relations
    products: fields.ReverseRelation["Product"]
    parent: fields.ForeignKeyNullableRelation["Category"] = fields.ForeignKeyField(
        "models.Category", 
        related_name="children", 
        null=True, 
        on_delete=fields.SET_NULL
    )
    children: fields.ReverseRelation["Category"]

    class Meta:
        table = "categories"
        unique_together = ("name", "merchant_id")
        indexes = [
            ("merchant_id", "is_active"),  # Index composite pour perf
        ]

    def __str__(self):
        return f"Category({self.name})"

    @property
    def products_count(self) -> int:
        """Nombre de produits actifs dans cette catégorie"""
        return self.products.filter(is_active=True).count()

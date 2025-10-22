import uuid
from tortoise import fields
from tortoise.models import Model

class BaseModel(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    # Nouveaux champs pour soft delete et audit
    is_active = fields.BooleanField(default=True)
    created_by = fields.UUIDField(null=True)  # User qui a créé l'entité

    class Meta:
        abstract = True

    async def soft_delete(self):
        """Soft delete au lieu de suppression physique"""
        self.is_active = False
        await self.save()
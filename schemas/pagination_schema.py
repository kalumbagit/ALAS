
from typing import Generic, TypeVar, List,Optional,Dict,Any
from pydantic import BaseModel

T = TypeVar("T")

#==============================================================
# Pagination générique pour les marchands
#==============================================================

class PaginatedResponseSchema(BaseModel, Generic[T]):
    items: List[T] = []
    limit: int
    offset: int
    page: int  # numéro de la page actuelle
    total: int  # nombre total d'éléments
    total_pages: int  # nombre total de pages
    has_next: bool
    has_previous: bool
    filters: Optional[Dict[str, Any]] = None  # 👈 pour tes filtres
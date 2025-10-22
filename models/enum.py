from enum import Enum

class CurrencyEnum(str, Enum):
    XAF = "XAF"
    USD = "USD" 
    EUR = "EUR"
    OTHER = "OTHER"

class ProductStatusEnum(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

class StockStatusEnum(str, Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock" 
    OUT_OF_STOCK = "out_of_stock"
    PREORDER = "preorder"
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ProductCategory(str, Enum):
    TV = "tv"
    REFRIGERATOR = "refrigerator"
    WASHING_MACHINE = "washing_machine"
    DRYER = "dryer"
    AC = "ac"
    SOUNDBAR = "soundbar"
    PROJECTOR = "projector"
    DISHWASHER = "dishwasher"


# Unified Product Model for scraped Hisense data
class Product(BaseModel):
    id: str
    name: str
    category: ProductCategory
    brand: str = "Hisense"
    specs: dict = Field(default_factory=dict, description="Technical specifications")
    features: list[str] = Field(default_factory=list, description="Key features")
    url: Optional[str] = None
    sizes: list[str] = Field(default_factory=list, description="Available sizes/variants")


# Query Models
class ParsedQuery(BaseModel):
    category: Optional[str] = Field(None, description="Product category or null if unspecified")
    use_case: Optional[str] = Field(None, description="Primary use case like gaming, family, bedroom")
    room_size: Optional[str] = Field(None, description="Room size description if mentioned")
    family_size: Optional[int] = Field(None, description="Family size if mentioned")
    capacity: Optional[str] = Field(None, description="Desired capacity (liters, kg, etc.)")
    size_preference: Optional[str] = Field(None, description="Screen size, appliance size preference")
    must_have_features: list[str] = Field(default_factory=list, description="Required features")
    keywords: list[str] = Field(default_factory=list, description="Other relevant keywords")


class RecommendationRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural language query")


class ProductRecommendation(BaseModel):
    product: Product
    score: float = Field(..., ge=0, le=100, description="Match score 0-100")
    reasoning: str = Field(..., description="Why this product is recommended")


class RecommendationResponse(BaseModel):
    query: str
    parsed_query: ParsedQuery
    recommendations: list[ProductRecommendation]
    message: str = Field(..., description="Summary message for the user")

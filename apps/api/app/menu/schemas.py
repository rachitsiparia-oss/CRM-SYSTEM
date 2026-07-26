import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

FoodType = Literal["vegetarian", "non_vegetarian"]
SpiceLevel = Literal["mild", "medium", "hot", "extra_hot"]
AvailabilitySource = Literal["manual", "inventory_derived", "schedule", "integration", "override"]


def _validated_code(value: str) -> str:
    stripped = value.strip().lower()
    if not stripped:
        raise ValueError("Code cannot be empty.")
    if not all(c.isalnum() or c in "-_" for c in stripped):
        raise ValueError("Code may only contain letters, numbers, hyphens, and underscores.")
    return stripped


class CategoryCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def _code(cls, v: str) -> str:
        return _validated_code(v)


class CategoryUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    is_active: bool | None = None
    expected_version: int | None = None


class CategoryReorderIn(BaseModel):
    ordered_category_ids: list[uuid.UUID] = Field(min_length=1)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    sort_order: int
    is_active: bool
    version: int


class ProductVariantIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    price_minor: int = Field(ge=0)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True
    is_available: bool = True
    preparation_minutes: int | None = Field(default=None, ge=0)


class ProductVariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    code: str
    name: str
    price_minor: int
    sort_order: int
    is_active: bool
    is_available: bool
    preparation_minutes: int | None
    version: int


class ProductCreateIn(BaseModel):
    category_id: uuid.UUID
    name: str = Field(min_length=1, max_length=180)
    display_name: str | None = Field(default=None, max_length=180)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=240)
    product_code: str | None = Field(default=None, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    food_type: FoodType = "vegetarian"
    is_jain_capable: bool = False
    is_vegan_capable: bool = False
    contains_egg: bool = False
    contains_dairy: bool = False
    contains_gluten: bool = False
    contains_nuts: bool = False
    contains_soy: bool = False
    contains_alcohol: bool = False
    spice_level: SpiceLevel | None = None
    preparation_minutes: int | None = Field(default=None, ge=0)
    calories: int | None = Field(default=None, ge=0)
    base_price_minor: int = Field(ge=0)
    tax_category: str | None = Field(default=None, max_length=64)
    dine_in_available: bool = True
    takeaway_available: bool = True
    delivery_available: bool = True
    sort_order: int = Field(default=0, ge=0)
    is_featured: bool = False
    is_chef_recommended: bool = False


class ProductUpdateIn(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=180)
    display_name: str | None = Field(default=None, max_length=180)
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=240)
    barcode: str | None = Field(default=None, max_length=64)
    food_type: FoodType | None = None
    is_jain_capable: bool | None = None
    is_vegan_capable: bool | None = None
    contains_egg: bool | None = None
    contains_dairy: bool | None = None
    contains_gluten: bool | None = None
    contains_nuts: bool | None = None
    contains_soy: bool | None = None
    contains_alcohol: bool | None = None
    spice_level: SpiceLevel | None = None
    preparation_minutes: int | None = Field(default=None, ge=0)
    calories: int | None = Field(default=None, ge=0)
    base_price_minor: int | None = Field(default=None, ge=0)
    tax_category: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None
    is_available: bool | None = None
    dine_in_available: bool | None = None
    takeaway_available: bool | None = None
    delivery_available: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)
    is_featured: bool | None = None
    is_chef_recommended: bool | None = None
    expected_version: int | None = None


class ProductAvailabilityOverrideIn(BaseModel):
    is_available: bool
    reason: str = Field(min_length=1, max_length=500)
    until: str | None = None


class ProductArchiveIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class ProductReorderIn(BaseModel):
    ordered_product_ids: list[uuid.UUID] = Field(min_length=1)


class ProductListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_code: str
    name: str
    display_name: str | None
    category_id: uuid.UUID
    food_type: str
    base_price_minor: int
    is_active: bool
    is_available: bool
    is_featured: bool
    sort_order: int
    image_storage_path: str | None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_code: str
    barcode: str | None
    category_id: uuid.UUID
    name: str
    display_name: str | None
    slug: str
    description: str | None
    short_description: str | None
    food_type: str
    is_jain_capable: bool
    is_vegan_capable: bool
    contains_egg: bool
    contains_dairy: bool
    contains_gluten: bool
    contains_nuts: bool
    contains_soy: bool
    contains_alcohol: bool
    spice_level: str | None
    preparation_minutes: int | None
    calories: int | None
    base_price_minor: int
    tax_category: str | None
    is_active: bool
    is_available: bool
    availability_source: str
    manual_override_reason: str | None
    dine_in_available: bool
    takeaway_available: bool
    delivery_available: bool
    image_storage_path: str | None
    sort_order: int
    is_featured: bool
    is_chef_recommended: bool
    version: int


class ModifierGroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    min_select: int = Field(default=0, ge=0)
    max_select: int = Field(default=1, ge=1)
    is_required: bool = False
    sort_order: int = Field(default=0, ge=0)


class ModifierGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    min_select: int
    max_select: int
    is_required: bool
    sort_order: int
    version: int


class ModifierIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    default_price_minor: int = Field(default=0, ge=0)
    is_active: bool = True


class ModifierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    default_price_minor: int
    is_active: bool
    version: int


class ModifierGroupItemIn(BaseModel):
    modifier_id: uuid.UUID
    price_minor_override: int | None = Field(default=None, ge=0)
    sort_order: int = Field(default=0, ge=0)
    is_available: bool = True


class ModifierGroupItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    modifier_group_id: uuid.UUID
    modifier_id: uuid.UUID
    price_minor_override: int | None
    sort_order: int
    is_available: bool


class ProductModifierGroupIn(BaseModel):
    modifier_group_id: uuid.UUID
    sort_order: int = Field(default=0, ge=0)


class ProductModifierGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID
    modifier_group_id: uuid.UUID
    sort_order: int


class ProductImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    alt_text: str | None
    sort_order: int
    is_thumbnail: bool
    file_size_bytes: int
    mime_type: str
    signed_url: str


class ProductImageReorderIn(BaseModel):
    ordered_image_ids: list[uuid.UUID] = Field(min_length=1)

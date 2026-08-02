from pydantic import BaseModel, Field


class CacheFamilyOut(BaseModel):
    family: str
    ttl_seconds: int


class CacheInvalidateIn(BaseModel):
    family: str = Field(min_length=1, max_length=64)

from fastapi import Request
from pydantic import BaseModel

from app.core.pagination import Meta


class DataResponse[T](BaseModel):
    """Standard single-resource envelope — DATABASE_AND_API.md section 19.3."""

    data: T
    meta: Meta


def request_meta(request: Request) -> Meta:
    return Meta(request_id=getattr(request.state, "request_id", ""))

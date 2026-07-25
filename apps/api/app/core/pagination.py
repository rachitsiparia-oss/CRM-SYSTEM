from pydantic import BaseModel, Field

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


class PageParams(BaseModel):
    """Offset-pagination query parameters shared by stable admin lists.

    High-volume, continuously changing feeds (messages, activity, audit
    events, notifications) use cursor pagination instead — see
    DATABASE_AND_API.md section 19.5. No endpoint may return an unbounded
    collection.
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int


class PaginatedResponse[T](BaseModel):
    data: list[T]
    pagination: Pagination

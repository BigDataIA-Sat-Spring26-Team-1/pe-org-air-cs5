from typing import List, TypeVar
from math import ceil
from app.models.common import PaginatedResponse

T = TypeVar('T')

def create_paginated_response(items: List[T], total: int, page: int, page_size: int) -> PaginatedResponse[T]:
    if total <= 0:
        total_pages = 0
    else:
        total_pages = ceil(total / page_size)
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

def get_offset(page: int, page_size: int) -> int:
    return (page - 1) * page_size

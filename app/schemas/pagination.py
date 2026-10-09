"""Paging primitives shared by every endpoint marked `is_paged` in a module's contract.

CLAUDE.md: "Paged endpoints accept `page`/`pageSize` (plus `search`/`sortBy`/`sortOrder` and
the endpoint's filters) and return the contract's paged response shape." `PageParams` binds
the request side; `PagedResponse` is a generic the contract's concrete paged DTO (e.g.
`ContractListResponse`) can reuse for its `items`/`page`/`pageSize`/`totalCount` fields.
"""
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

ItemT = TypeVar("ItemT")


class PageParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        pageSize: int = Query(20, ge=1, le=200),
        search: str | None = Query(None),
        sortBy: str | None = Query(None),
        sortOrder: str | None = Query(None, pattern="^(asc|desc)$"),
    ) -> None:
        self.page = page
        self.page_size = pageSize
        self.search = search
        self.sort_by = sortBy
        self.sort_order = sortOrder

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PagedResponse(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    page: int
    pageSize: int
    totalCount: int

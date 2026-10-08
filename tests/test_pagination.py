from fastapi import Depends

from app.main import app
from app.schemas.pagination import PageParams


@app.get("/_test/paged")
def _paged(params: PageParams = Depends()) -> dict:
    return {
        "page": params.page,
        "pageSize": params.page_size,
        "search": params.search,
        "sortBy": params.sort_by,
        "sortOrder": params.sort_order,
        "offset": params.offset,
    }


def test_pagination_defaults(client):
    resp = client.get("/_test/paged")
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["pageSize"] == 20
    assert body["offset"] == 0


def test_pagination_overrides(client):
    resp = client.get(
        "/_test/paged",
        params={"page": 3, "pageSize": 10, "search": "acme", "sortBy": "name", "sortOrder": "desc"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 3
    assert body["pageSize"] == 10
    assert body["offset"] == 20
    assert body["search"] == "acme"
    assert body["sortBy"] == "name"
    assert body["sortOrder"] == "desc"


def test_pagination_rejects_invalid_sort_order(client):
    resp = client.get("/_test/paged", params={"sortOrder": "sideways"})
    assert resp.status_code == 400

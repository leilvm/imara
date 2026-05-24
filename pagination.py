from rest_framework.pagination import CursorPagination


class ImaraCursorPagination(CursorPagination):
    """
    Cursor-based pagination for Imara API feeds.

    Chosen over offset pagination for two reasons:
    1. Stable results: new records inserted while a lender browses will not
       cause items to shift pages (no skipped or duplicated results).
    2. No COUNT(*) query: cheaper on large tables and returns smaller JSON
       payloads — important for low-bandwidth field agents.

    Clients receive opaque `next` and `previous` cursor URLs.
    They cannot jump to an arbitrary page number by design.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"
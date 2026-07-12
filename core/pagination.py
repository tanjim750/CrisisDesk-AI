from core.responses.renderer import paginated_response

try:
    from rest_framework.pagination import PageNumberPagination
except ImportError:
    PageNumberPagination = object


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return paginated_response(
            request=self.request,
            code=getattr(self, "response_code", "REPORTS_RETRIEVED"),
            data=data,
            pagination=self,
            count=getattr(self.page.paginator, "count", len(data)),
        )

    @property
    def count(self):
        page = getattr(self, "page", None)
        paginator = getattr(page, "paginator", None)
        return getattr(paginator, "count", None)

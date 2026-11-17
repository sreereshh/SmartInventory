from datetime import date, datetime

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


def paginate(request, items, per_page=10):
    """Return (page_obj, querystring_without_page) for template pagination."""
    paginator = Paginator(items, per_page)
    page_number = request.GET.get("page", 1)
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    params = request.GET.copy()
    params.pop("page", None)
    return page, params.urlencode()


def parse_date(value, default=None):
    """Parse YYYY-MM-DD; return default on failure."""
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


def parse_month(value, default=None):
    """Parse YYYY-MM into a (year, month) tuple; return default on failure."""
    if not value:
        return default
    try:
        parsed = datetime.strptime(value, "%Y-%m")
        return parsed.year, parsed.month
    except (TypeError, ValueError):
        return default

from django import template

register = template.Library()

@register.inclusion_tag('pagination.html')
def render_pagination(page_number, total_pages, limit=10):
    """
    Template tag for render pagination

    Args:
    - page_number: number of actual page
    - total_pages: total pages.

    Use it template: {% render_pagination page_number total_pages %}
    """
    return {
        'page_number': page_number,
        'total_pages': total_pages,
        'limit': limit
    }

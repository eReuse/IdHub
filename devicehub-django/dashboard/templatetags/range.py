from django import template

register = template.Library()


@register.filter
def range_filter(value, page):
    m = 11
    mind = page -1 - m // 2
    maxd = page + 1 +  m // 2
    if mind < 0:
        maxd += abs(mind)
    if maxd > value:
        mind -= abs(maxd-value-1)
    total_pages = [x for x in range(1, value + 1) if maxd > x > mind]

    if  value > m:
        if total_pages[0] > 1:
            total_pages = ["..."] + total_pages
        if total_pages[-1] < value:
            total_pages = total_pages + ["..."]

    return total_pages

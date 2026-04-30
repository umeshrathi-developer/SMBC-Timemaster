from django import template

register = template.Library()


@register.filter
def get_item(list_obj, index):
    """
    Get item from list by index.
    Usage: {{ list_obj|get_item:0 }}
    """
    try:
        return list_obj[index]
    except (IndexError, KeyError, TypeError):
        return None


@register.filter
def get_index(list_obj, index):
    """
    Backward-compatible alias for list access by index.
    Usage: {{ list_obj|get_index:0 }}
    """
    return get_item(list_obj, index)


@register.filter
def in_list(date_obj, date_list):
    """
    Check if a date is in a list of dates.
    Usage: {% if entry.date|in_list:holiday_dates %}
    """
    try:
        return date_obj in date_list
    except (TypeError, AttributeError):
        return False

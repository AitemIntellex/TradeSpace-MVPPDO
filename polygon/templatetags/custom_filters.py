from django import template

register = template.Library()


@register.filter
def zip_lists(a, b):
    """Zips two lists together."""
    return zip(a, b)


@register.filter
def split(value, arg):
    """Splits a string by the given delimiter."""
    return value.split(arg)


@register.filter
def get_item(dictionary, key):
    """
    Возвращает значение из словаря по ключу.
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def get_nested_item(dictionary, keys):
    """
    Access nested dictionary items using comma-separated keys.
    Example usage: "outer_key,inner_key"
    """
    keys = keys.split(",")
    result = dictionary
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
        else:
            return None
    return result


@register.filter(name="get_value")
def get_value(dictionary, key):
    """
    Gets a value from a dictionary by key with a fallback "-".
    Usage: {{ my_dict|get_value:my_key }}
    """
    return dictionary.get(key, "-") if isinstance(dictionary, dict) else "-"


@register.filter
def dict_items(value):
    """
    Returns key-value pairs of a dictionary.
    Usage: {{ my_dict|dict_items }}
    """
    return value.items() if isinstance(value, dict) else None


@register.filter
def get_nearest(values, price):
    """
    Finds the closest number in a list to the given price.
    """
    if not values or price is None:
        return None
    return min(values, key=lambda x: abs(x - price))


@register.filter
def in_list(value, arg):
    """
    Проверяет, находится ли значение в списке (переданном как строка, разделённая запятыми).
    Пример: {% if value|in_list:"-61.8%,61.8%,161.8%" %}
    """
    return value in arg.split(",")


@register.filter
def is_string(value):
    """
    Проверяет, является ли значение строкой.
    """
    return isinstance(value, str)


# templatetags/custom_filters.py
from django import template

register = template.Library()


@register.filter
def get_value(dictionary, key):
    return dictionary.get(key, None)


@register.filter
def concat(value, arg):
    """Concatenates value and arg"""
    return f"{value}{arg}"

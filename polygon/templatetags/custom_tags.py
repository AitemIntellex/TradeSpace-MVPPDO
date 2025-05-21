from django import template

register = template.Library()


@register.filter(name="get_value")
def get_value(dictionary, key):
    """
    Позволяет получить значение из словаря по ключу в шаблоне.
    Использование: {{ my_dict|get_value:my_key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, "-")
    return "-"

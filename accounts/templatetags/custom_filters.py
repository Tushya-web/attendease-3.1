from django import template
import os

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Safely get value from a dictionary by key.
    Usage: {{ dict|get_item:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, "")
    return ""

@register.filter
def basename(value):
    """
    Return just the file name (no path).
    Usage: {{ file_path|basename }}
    """
    if not value:
        return ""
    return os.path.basename(str(value))

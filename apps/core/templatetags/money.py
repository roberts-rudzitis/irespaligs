from django import template

from apps.core.money import format_eur, format_quantity

register = template.Library()


@register.filter
def eur(value):
    """Usage: {% load money %} {{ amount|eur }} → 1 234,56 €"""
    return format_eur(value)


@register.filter
def qty(value):
    """Usage: {{ reading|qty }} → 120,4 (no trailing zeros, decimal comma)"""
    return format_quantity(value)

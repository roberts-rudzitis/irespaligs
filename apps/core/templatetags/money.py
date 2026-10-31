from django import template

from apps.core.money import format_eur

register = template.Library()


@register.filter
def eur(value):
    """Usage: {% load money %} {{ amount|eur }} → 1 234,56 €"""
    return format_eur(value)

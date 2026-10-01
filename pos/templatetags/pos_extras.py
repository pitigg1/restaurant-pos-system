from django import template

register = template.Library()

# Dict lookup by variable key, since Django templates can't do dict[key].
@register.filter
def get_item(d, k):
    if not d:
        return None
    try:
        return d.get(k)
    except Exception:
        return None

# Colombian peso formatting: 48000 -> "$ 48.000".
@register.filter
def cop(value):
    try:
        n = int(round(float(value or 0)))
    except (TypeError, ValueError):
        return value
    sign = "-" if n < 0 else ""
    return f"{sign}$ {abs(n):,}".replace(",", ".")

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
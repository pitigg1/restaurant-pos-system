from pos.models import BusinessConfig

def business_config(request):
    """Makes {{ business }} available in every template."""
    try:
        config = BusinessConfig.get_config()
    except Exception:
        config = None
    return {"business": config}

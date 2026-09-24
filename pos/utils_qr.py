# pos/utils_qr.py
from __future__ import annotations
from pathlib import Path
import socket
import qrcode
from django.conf import settings


def get_local_ip() -> str:
    """
    Gets the real local IP (the one Windows uses to reach the network).
    Works fine on Wi-Fi / hotspot.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually connect, just forces interface selection.
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def build_base_url(request=None, port: int = 8000) -> str:
    """
    Uses the real request host when available, otherwise falls back
    to the local IP.
    """
    if request is not None:
        # Respect the request's actual host/port.
        scheme = "https" if request.is_secure() else "http"
        host = request.get_host()  # may include :8000
        return f"{scheme}://{host}"
    ip = get_local_ip()
    return f"http://{ip}:{port}"


def generate_staff_qrs(base_url: str) -> dict:
    """
    Generates PNG QR codes in static/pos/qrs/.
    Returns relative paths for rendering in templates.
    """
    out_dir = Path(settings.BASE_DIR) / "pos" / "static" / "pos" / "qrs"
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = {
        "Meseras": f"{base_url}/pos/waiter/tables/",
        "Cocina": f"{base_url}/pos/kitchen/",
        "Admin": f"{base_url}/pos/admin/",
        "Login": f"{base_url}/pos/login/",
    }

    results = {}
    for label, url in targets.items():
        img = qrcode.make(url)
        filename = f"qr_{label.lower().replace(' ', '_')}.png"
        img.save(out_dir / filename)
        results[label] = f"pos/qrs/{filename}"  # relative to STATIC_URL

    return results

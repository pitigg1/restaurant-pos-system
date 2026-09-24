# Restaurant POS System 

A complete restaurant point-of-sale system built for "Las Hamacas". It covers table management, real-time order tracking, a kitchen display, administration, and payments.

## Key Features

### Kitchen Display System (KDS)
- Live view of pending orders
- Status flow: New -> In Preparation -> Ready
- Real-time updates via WebSockets
- Orders organized by zone and table

### Waiter Module
- Visual table selection, grouped by zone
- Create and edit orders
- Live status per table
- Integrated checkout with tips
- Thermal ticket printing

### Admin Panel
- Sales dashboard with statistics
- Full menu management (categories and items)
- User and role administration
- Business configuration (name, logo, tips)
- Zone and table management
- Full order and sales history
- QR code generation for each table

### Payments
- Multiple methods: cash, Nequi, bank transfer
- Configurable tips (fixed amount or percentage)
- Automatic ticket printing
- Full transaction records

### Real Time
- Instant order status updates
- Kitchen and waiter screens stay in sync
- Push notifications via WebSockets (Django Channels)

## Tech Stack

### Backend
- **Django 5.2** - web framework
- **Django Channels** - WebSockets for real-time communication
- **SQLite** - database (development; PostgreSQL recommended for production)
- **Python 3.11+**

### Frontend
- **HTML5 + CSS3**, hand-written per screen (no CSS framework)
- **Vanilla JavaScript** - no jQuery or frontend framework
- **WebSocket API** - real-time client updates

### Infrastructure
- **Daphne** - ASGI server (serves both HTTP and WebSockets)
- **Redis** (optional) - Channels backend for production/multi-worker setups
- **python-decouple** - environment variable management

## Requirements

- Python 3.11 or newer
- pip
- A virtual environment (recommended)
- Redis (optional, production only)
- An ESC/POS-compatible thermal printer (optional)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/SistemaHamacas.git
cd SistemaHamacas
```

### 2. Create and activate a virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file and edit it:

```bash
cp .env.example .env
```

Set at least:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=*
RECEIPT_PRINTER_NAME=your-printer-name
USE_REDIS=0
```

Generate a secure `SECRET_KEY`:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Seed initial data

**Zones and business config:**
```bash
python manage.py seed_zones
```

**Test users:**
```bash
python manage.py seed_users
```

This creates:
- **Admin:** `admin` / `admin123`
- **Manager:** `gerente` / `gerente123`
- **Waiters:** `mesero1`-`mesero4` / `mesero123`
- **Kitchen:** `cocina1`, `cocina2`, `chef` / `cocina123` or `chef123`

**Sample menu (optional):**
```bash
python manage.py seed_menu
```

### 7. Collect static files

```bash
python manage.py collectstatic --noinput
```

### 8. Run the server

**Development:**
```bash
python manage.py runserver
```

**Production (via Daphne):**
```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Then open `http://localhost:8000/pos/`.

## Roles and Permissions

### Admin
- Full system access
- Statistics dashboard
- Menu, user, zone and table management
- Business configuration
- Full order and sales history

### Waiter
- Table view grouped by zone
- Create and edit orders
- Process payments
- Live order status

### Kitchen
- Kitchen Display System (KDS)
- Change order status
- View order details
- Orders organized by zone

## Project Structure

```
SistemaHamacas/
├── config/                 # Django project configuration
│   ├── settings.py         # Main settings
│   ├── urls.py             # Root URL configuration
│   ├── asgi.py             # ASGI entry point (HTTP + WebSockets)
│   └── routing.py          # WebSocket routing
├── core/                   # User app
│   └── models.py           # Custom User model
├── pos/                    # Main POS app
│   ├── models.py           # Order, MenuItem, Zone, etc.
│   ├── views/               # Views split by module
│   │   ├── api.py           # JSON API endpoints
│   │   ├── admin_views.py   # Admin screens
│   │   ├── waiter.py        # Waiter screens
│   │   └── kitchen.py       # Kitchen screens
│   ├── consumers.py         # WebSocket consumers
│   ├── templates/           # HTML templates
│   ├── static/               # Static assets
│   │   ├── js/                # JavaScript (spinner.js, etc.)
│   │   └── pos/                # CSS, icons, logo
│   └── management/
│       └── commands/          # seed_zones, seed_users, seed_menu
├── logs/                    # Application logs (created at runtime)
├── staticfiles/              # Collected static files (generated)
├── media/                    # Uploaded files, e.g. the business logo (generated)
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

## Management Commands

### Standard Django commands

```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run tests
python manage.py test

# Interactive shell
python manage.py shell
```

### Custom commands

```bash
# Create initial zones and tables
python manage.py seed_zones

# Create test users
python manage.py seed_users

# Seed the menu with sample data
python manage.py seed_menu

# Wipe and recreate users
python manage.py seed_users --clear

# Update existing users with the seed data
python manage.py seed_users --update

# Wipe and recreate the menu
python manage.py seed_menu --clear
```

## API Endpoints (quick reference)

All endpoints require an authenticated session.

### Menu
- `GET /pos/api/menu/` - list available menu items

### Orders
- `GET /pos/api/orders/active/<zone>/<table>/` - active order for a table
- `POST /pos/api/orders/create/` - create a new order
- `POST /pos/api/orders/<id>/edit/` - replace an order's items
- `POST /pos/api/orders/<id>/cancel/` - cancel an order
- `POST /pos/api/orders/<id>/finish/` - mark an order as done
- `POST /pos/api/orders/<id>/status/` - change status (kitchen)
- `POST /pos/api/orders/<id>/pay/` - process payment

### Kitchen
- `GET /pos/api/kitchen/orders/` - active orders for the KDS

### Admin
- `GET /pos/api/admin/analytics/` - sales series for the dashboard chart
- `GET /pos/api/admin/order/<id>/` - full order detail

Full request/response documentation lives in [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

## Security

### Development
- `DEBUG=True` shows detailed error pages
- `SECRET_KEY` can be a throwaway value
- `ALLOWED_HOSTS=*` allows any host

### Production
- **`DEBUG=False`** (critical)
- `SECRET_KEY` must be unique, complex and kept secret
- `ALLOWED_HOSTS` should list only the allowed domains
- Serve over HTTPS with the secure cookie/HSTS settings enabled
- Use Redis as the Channels backend
- Configure logging and monitoring

See [.env.production.example](.env.production.example) for a complete production configuration.

## Printer Setup

### Windows

1. Install the thermal printer as a Windows printer.
2. Note its exact name (Control Panel > Devices and Printers).
3. Set it in `.env`:

```env
RECEIPT_PRINTER_NAME=SAT38TUSE
```

### Requirements
- ESC/POS-compatible printer
- Driver installed on Windows
- `pywin32` package (already listed in requirements.txt)

## Testing

### Run the full suite

```bash
python manage.py test
```

### Run specific tests

```bash
# Model tests
python manage.py test pos.tests.BusinessConfigModelTest

# API tests
python manage.py test pos.tests.MenuAPITest

# Authentication tests
python manage.py test pos.tests.AuthenticationTest
```

## Logging

Logs are written to the `logs/` directory:

- `app.log` - general application log
- `errors.log` - errors only
- `security.log` - security-related events

Set the log level in `.env`:
```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Production Deployment

### Preparation

1. **Set production environment variables:**
   ```bash
   cp .env.production.example .env
   # edit .env with production values
   ```

2. **Install Redis:**
   ```bash
   sudo apt-get install redis-server
   sudo systemctl start redis
   ```

3. **Configure the database** (PostgreSQL recommended):
   ```bash
   DATABASE_URL=postgres://user:password@localhost:5432/pos_hamacas
   ```

4. **Apply migrations and collect static files:**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

5. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```

### Running with Daphne

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### Behind Nginx (recommended)

```nginx
upstream django {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/SistemaHamacas/staticfiles/;
    }

    location /media/ {
        alias /path/to/SistemaHamacas/media/;
    }

    location / {
        proxy_pass http://django;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd service

Create `/etc/systemd/system/hamacas-pos.service`:

```ini
[Unit]
Description=Hamacas POS
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/SistemaHamacas
Environment="PATH=/path/to/SistemaHamacas/venv/bin"
ExecStart=/path/to/SistemaHamacas/venv/bin/daphne -b 0.0.0.0 -p 8000 config.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl enable hamacas-pos
sudo systemctl start hamacas-pos
```

## Troubleshooting

### "No module named 'decouple'"
```bash
pip install python-decouple
```

### WebSockets are not working
1. Confirm Daphne is actually running the process (not `runserver` under WSGI).
2. If you're behind Nginx, check the WebSocket proxy headers (`Upgrade`/`Connection`).
3. In production with more than one worker, make sure `USE_REDIS=1`.

### The printer doesn't print
1. Confirm `RECEIPT_PRINTER_NAME` matches the printer's exact Windows name.
2. Confirm `pywin32` is installed.
3. Confirm the printer is connected and powered on.

### "CSRF token missing"
1. Make sure `{% csrf_token %}` is present in the form.
2. For AJAX requests, send the token in the headers:
   ```javascript
   headers: {
       'X-CSRFToken': getCookie('csrftoken')
   }
   ```

## License

This project is private and proprietary to Las Hamacas.

## Contact

- Email: soporte@lashamacas.com

## Roadmap

- Sales reports in PDF/Excel
- Advanced analytics charts
- Inventory management
- Payment gateway integration (e.g. PSE, Mercado Pago)
- Native mobile app
- Reservation system
- Customer loyalty program

# Tech Stack & Build

## Core Framework

- **Python 3 + Django 4.2** (LTS)
- **Django REST Framework 3.15** for JSON API endpoints
- **Django Templates + Bootstrap 5** for the frontend (server-rendered HTML)
- **Crispy Forms + crispy-bootstrap5** for form rendering

## Key Libraries

| Library | Purpose |
|---------|---------|
| python-decouple | Environment variable management (.env) |
| dj-database-url | Database URL parsing |
| psycopg2-binary | PostgreSQL adapter |
| whitenoise | Static file serving in production |
| django-cloudinary-storage + cloudinary | Persistent media storage |
| pillow | Image processing (profile pics, logos) |
| openpyxl | Excel export |
| reportlab | PDF generation |
| gunicorn | Production WSGI server |

## Frontend

- **No JS build step** — plain vanilla JS in `static/js/`
- **Lucide icons** (via bundled `lucide.min.js`)
- **Bootstrap 5** loaded via CDN or static
- **AJAX navigation** using custom `ajax-nav.js` with fragment markers in templates
- **CSS**: custom `style.css` + `skeleton.css` for loading states

## Database

- **Production & Local**: Neon PostgreSQL (configured via `DATABASE_URL` env var)
- **Caching**: File-based Django cache (`django_cache/`)
- **Sessions**: `cached_db` backend

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create the default super admin
python manage.py create_superadmin

# Seed sample data
python manage.py seed_data

# Collect static files
python manage.py collectstatic --no-input

# Run development server
python manage.py runserver

# Full production build (used on Render)
bash build.sh
```

## Environment Variables (.env)

Key variables: `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CLOUDINARY_URL` (or `CLOUDINARY_CLOUD_NAME` + `CLOUDINARY_API_KEY` + `CLOUDINARY_API_SECRET`), `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`.

## Settings Notes

- `AUTH_USER_MODEL = 'accounts.User'` (custom user model)
- Timezone: `Asia/Manila`
- File uploads limited to 10 MB; allowed extensions: pdf, doc(x), xls(x), jpg, jpeg, png, zip
- REST API uses session auth with rate throttling (30 anon / 120 user per minute)
- Security headers enabled; HTTPS enforced in production

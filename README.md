# CSG Task Management and Monitoring System

A full-featured Django-based task management system for a university student government organization.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, Django 4.2, Django REST Framework |
| Frontend | HTML5, CSS3, Bootstrap 5.3, Vanilla JS |
| Charts | Chart.js 4.x |
| Database | PostgreSQL 15.4 |
| PDF Export | ReportLab |
| Excel Export | openpyxl |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations
python manage.py migrate

# 3. Seed sample data
python manage.py seed_data

# 4. Start the server
python manage.py runserver
```

Access at: **http://127.0.0.1:8000/**

## Login Credentials

| Role | Username | Password |
|---|---|---|
| Super Admin | `admin` | `csg2025` |
| President | `president` | `csg2025` |
| Vice President | `vp_juan` | `csg2025` |
| Secretary | `sec_anna` | `csg2025` |
| Treasurer | `treas_ben` | `csg2025` |
| All others | see below | `csg2025` |

Other usernames: `auditor_lea`, `pro_chris`, `bm_rose`, `ext_mark`, `asec_jen`, `atreas_mike`

## Features

### Dashboard
- 4 stat cards: Active, Completed, Overdue, Due This Week
- 5 Chart.js visualizations (Doughnut, Bar, Pie, Horizontal Bar, Line)
- Recent tasks table with live data

### Task Management
- Create/edit/delete tasks
- Auto-generated task numbers (CSG-YYYY-####)
- Assign multiple officers
- Set priority and status
- Progress tracking (0-100%)
- Comments and attachments
- History/audit trail
- Archive completed tasks
- Export to PDF and Excel

### Task Statuses
- Pending · Not Started · In Progress · Waiting Approval · Completed · Overdue · Cancelled

### Priority Levels
- Low · Medium · High · Urgent

### Monitoring
- Officer productivity ranking
- Department performance
- Upcoming deadlines (7-day view)
- Overdue tasks list

### Reports
- Filter by officer, department, month, year, status, priority
- Export PDF and Excel

### Notifications
- Task assignment notifications
- Due date reminders
- Completion notifications
- Mark as read / Mark all read

### User Roles
| Feature | Super Admin | President | Executive | Committee Head |
|---|---|---|---|---|
| Manage Officers | ✅ | ❌ | ❌ | ❌ |
| Create Tasks | ✅ | ✅ | ❌ | ❌ |
| View All Tasks | ✅ | ✅ | ❌ | ❌ |
| Update Progress | ✅ | ✅ | ✅ | ✅ |
| Generate Reports | ✅ | ✅ | ❌ | ❌ |

## Project Structure

```
d:\CSG\
├── manage.py
├── requirements.txt
├── .env
├── csg_project/        # Django settings/URLs
├── accounts/           # Auth, profiles, roles
├── core/               # Dashboard, settings, seed command
├── officers/           # Officers, departments, positions
├── tasks/              # Task CRUD, API, export
├── monitoring/         # Analytics dashboard
├── reports/            # Report generation/export
├── notifications/      # Notification system
├── templates/          # HTML templates
└── static/             # CSS, JS, images
```

## API Endpoints

```
GET  /api/dashboard/stats/        → Dashboard stat cards
GET  /api/dashboard/charts/       → All chart data (JSON)
GET  /api/tasks/                  → Task list
GET  /api/tasks/<id>/             → Task detail
GET  /api/notifications/unread/   → Unread notifications
POST /api/notifications/<id>/read/ → Mark notification read
```

## PostgreSQL Setup (Production)

Update `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/csg_db
```

Update `settings.py` DATABASES:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'csg_db',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Install: `pip install psycopg2-binary`

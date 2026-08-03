# CSG Task Management and Monitoring System

A comprehensive, multi-tenant Django-based Task Management and Monitoring System designed for university student government organizations (CSG, CO:DE, ACES, etc.).

---

## 🚀 Prerequisites

Before setting up the project locally, ensure you have the following installed on your machine:
* **Python**: `3.10` or higher ([Download Python](https://www.python.org/downloads/))
* **Git**: ([Download Git](https://git-scm.com/))
* **Pip**: Python package manager (included with Python)

---

## 🛠️ Step-by-Step Setup Guide

### 1. Clone the Repository
Open your terminal/command prompt and clone the repository:
```bash
git clone https://github.com/ZythTheCode/csg_task.git
cd csg_task
```

### 2. Create and Activate a Virtual Environment

* **On Windows (PowerShell)**:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
* **On Windows (Command Prompt)**:
  ```cmd
  python -m venv .venv
  \.venv\Scripts\activate.bat
  ```
* **On macOS / Linux**:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install Required Dependencies
With the virtual environment activated, install all required packages:
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables (`.env`)
Create a `.env` file in the root project directory (`csg_task/.env`):

```ini
DEBUG=True
SECRET_KEY=django-insecure-csg-local-secret-key-development-mode-12345
ALLOWED_HOSTS=127.0.0.1,localhost
ENABLE_SEED_DATA=True
# DATABASE_URL is optional for local dev. If omitted, Django defaults to SQLite.
```

### 5. Run Database Migrations
Create the database tables:
```bash
python manage.py migrate
```

### 6. Populate Seed Data & Create Admin Accounts
Initialize sample organizations, user accounts, position titles, and sample tasks:
```bash
python manage.py seed_data
```

*(Optional)* Create a new custom Super Admin account manually:
```bash
python manage.py createsuperuser
```

### 7. Run the Development Server
Start the local server:
```bash
python manage.py runserver
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 🔑 Default Credentials

| Username | Full Name | System Role | Organization | Default Password |
| :--- | :--- | :--- | :--- | :--- |
| **`admin`** | Admin CSG | Super Admin | Central Student Government (CSG) | `csg2025` |
| **`president`** | Zyron Asty Bustamante | President | Central Student Government (CSG) | `csg2025` |
| **`vp_juan`** | Boris Alano | Elected Officer (VP) | Central Student Government (CSG) | `csg2025` |
| **`sec_anna`** | Jazel Moradas | Elected Officer (Secretary) | Central Student Government (CSG) | `csg2025` |
| **`treas_ben`** | Benjamin Torres | Elected Officer (Treasurer) | Central Student Government (CSG) | `csg2025` |
| **`auditor_lea`** | Lea Garcia | Elected Officer (Auditor) | Central Student Government (CSG) | `csg2025` |
| **`pro_chris`** | Christopher Lim | Elected Officer (P.R.O.) | Central Student Government (CSG) | `csg2025` |
| **`bm_rose`** | Roselyn Cruz | Elected Officer (Business Mgr) | Central Student Government (CSG) | `csg2025` |
| **`ea_mark`** | Mark Villanueva | Elected Officer (Exec Asst) | Central Student Government (CSG) | `csg2025` |
| **`asec_jen`** | Jennifer Bautista | Committee Member (Asst Sec) | Central Student Government (CSG) | `csg2025` |
| **`atreas_mike`** | Michael Ramos | Committee Member (Asst Treas) | Central Student Government (CSG) | `csg2025` |
| **`codeadmin`** | Bian Avan Toledo | Organization Admin | CO:DE | `csg2025` |
| **`em_david`** | David Flores | Committee Member (Events Mgr) | CO:DE | `csg2025` |
| **`gm_sophia`** | Sophia Mendoza | Committee Member (Graphics) | CO:DE | `csg2025` |
| **`pv_alex`** | Alex Navarro | Elected Officer (P.V.) | CO:DE | `csg2025` |
| **`acesadmin`** | John Doe | Organization Admin | ACES | `csg2025` |

---

## 🏛️ Roles & Access Overview

| Role | Access Description |
| :--- | :--- |
| **Super Admin** | Full access to all organizations, users, positions, tasks, settings, and system activity logs. |
| **Org Admin** | Scoped admin management over their organization's officers, positions, and tasks. |
| **President** | Executive task control (create/edit tasks, reassign officers, override stage transitions). |
| **Elected Officer** | View task boards/reports and update progress/remarks on assigned tasks. |
| **Committee Member** | Execute tasks, update progress percentages, and upload proof of work. |

---

## 📁 Project Architecture

```text
csg_task/
├── manage.py
├── requirements.txt
├── .env
├── csg_project/        # Core Django settings & main URLs
├── accounts/           # User authentication, roles, custom user model
├── core/               # Settings, branding themes, audit logger, seed command
├── officers/           # Officers, positions, role management
├── organizations/      # Multi-tenant organization registration & management
├── tasks/              # Task CRUD, Kanban board, REST API, PDF/Excel export
├── monitoring/         # Real-time analytics dashboard
├── reports/            # Performance analytics & reporting views
├── notifications/      # System notifications & nudges
├── templates/          # HTML5 templates & Bootstrap styling
└── static/             # Static CSS, JS, favicons & assets
```

---

## 🛠️ Troubleshooting

* **Static Files Not Loading**: Run `python manage.py collectstatic --noinput`
* **Database Errors / Out of Sync**: Remove `db.sqlite3` and re-run `python manage.py migrate` followed by `python manage.py seed_data`.
* **Port Already in Use**: Run on a different port: `python manage.py runserver 8080`.

# Design Document: Performance Optimization

## Overview

<<<<<<< HEAD
This design addresses server-side performance optimization for the CSG Task Management System — a Django 4.2 application running on Neon PostgreSQL (free tier), deployed on Render with WhiteNoise serving static files and file-based Django cache for application caching.

The optimization targets ten key areas: database query consolidation, indexing strategy, caching architecture, static file delivery, API response efficiency, middleware ordering, template rendering, connection persistence, permission check optimization, and export batching. All changes operate within existing free-tier infrastructure constraints (no Redis, no Celery, no additional workers).

### Design Rationale

The current codebase already uses some optimization patterns (conditional aggregation on dashboard, select_related in list views, cached notification counts). However, several views still issue redundant queries (Kanban board fires per-column queries, reports view counts separately, DashboardCharts API loops per-month), and the static pipeline lacks compression. This design standardizes and extends existing patterns across all views and API endpoints.
=======
This design covers a comprehensive performance optimization of the CSG Task Management System across six layers: database queries, caching, static assets, deployment configuration, frontend rendering, and observability. The optimizations target measurable bottlenecks identified in the current codebase — N+1 queries in board/chart views, redundant count() calls in reports, per-object loops in bulk operations, sub-optimal static file serving, and missing database indexes.

The approach follows the principle of smallest safe change: each optimization preserves tenant isolation, role-based access, and response semantics. No public URL patterns, response formats, or permission behaviors change.

**Key Design Decisions:**
1. Keep file-based cache (no Redis) — Render free-tier constraint, already in place
2. Use `gunicorn.conf.py` over render.yaml inline args — easier to version and test
3. Add performance middleware only in DEBUG mode — zero overhead in production
4. Prefer Django ORM aggregation over raw SQL — maintains portability and readability
5. Use `bulk_update`/`bulk_create` with explicit field lists — safe, auditable bulk ops
>>>>>>> fix/optimization

## Architecture

```mermaid
<<<<<<< HEAD
flowchart TB
    subgraph Request["Request Pipeline"]
        direction TB
        A[Client Request] --> B[GZipMiddleware]
        B --> C[SecurityMiddleware]
        C --> D[WhiteNoiseMiddleware]
        D -->|Static File| E[Compressed Static Response]
        D -->|Dynamic Request| F[SessionMiddleware]
        F --> G[AuthenticationMiddleware]
        G --> H[View Layer]
    end

    subgraph View["View Layer"]
        direction TB
        H --> I{Cache Hit?}
        I -->|Yes| J[Return Cached Response]
        I -->|No| K[Query Optimizer]
        K --> L[Single Aggregated Query]
        L --> M[File-Based Cache Set]
        M --> N[Template Render / JSON Serialize]
    end

    subgraph DB["Database Layer"]
        direction TB
        L --> O[PostgreSQL via Persistent Connection]
        O --> P[Composite Indexes]
    end
```

### Middleware Stack Order (Final)

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

**Rationale**: SecurityMiddleware sets HSTS/security headers on all responses. GZipMiddleware compresses dynamic HTML/JSON responses. WhiteNoise intercepts `/static/` requests and short-circuits the rest of the middleware stack for those, serving pre-compressed files with immutable caching headers.

## Components and Interfaces

### 1. Query Optimizer Patterns

#### Conditional Aggregation (Dashboard, Stats API, Reports)

Replace multiple `count()` calls with a single `aggregate()` using conditional `Count`:

```python
from django.db.models import Count, Q

counts = base_qs.aggregate(
    active=Count('id', filter=Q(status__in=active_statuses)),
    completed=Count('id', filter=Q(status='completed')),
    overdue=Count('id', filter=Q(due_date__lt=today, status__in=active_statuses)),
    upcoming=Count('id', filter=Q(
        due_date__gte=today,
        due_date__lte=today + timedelta(days=7),
        status__in=active_statuses
    )),
)
```

This pattern applies to: `DashboardView`, `DashboardStatsAPIView`, `DashboardChartsAPIView` (status/priority distributions), and `ReportsDashboardView`.

#### TruncMonth Aggregation (Charts API)

Replace per-month loop queries with a single `TruncMonth` annotation:

```python
from django.db.models.functions import TruncMonth

monthly = (
    base_qs
    .filter(status='completed')
    .annotate(month=TruncMonth('completion_date'))
    .values('month')
    .annotate(count=Count('id'))
    .order_by('month')
)
```

#### Kanban Board Single-Fetch Partitioning

Fetch all tasks in one queryset, then partition in Python:

```python
all_tasks = list(
    base_qs
    .exclude(status='completed')
    .select_related('created_by', 'organization')
    .prefetch_related(
        'assigned_officers',
        'assigned_officers__officer_profile',
        'assigned_officers__officer_profile__position'
    )
    .order_by('-created_at')
)

columns = []
for status_code, status_label in Task.STATUS_CHOICES:
    if status_code in ['overdue', 'completed']:
        continue
    group = [t for t in all_tasks if t.status == status_code]
    columns.append({
        'code': status_code,
        'label': status_label,
        'tasks': group[:50],
        'count': len(group),
    })
```

#### Select/Prefetch Chains

Standard chain for task-related querysets:

```python
qs.select_related('created_by', 'organization').prefetch_related(
    'assigned_officers',
    'assigned_officers__officer_profile',
    'assigned_officers__officer_profile__position'
)
```

### 2. Database Index Strategy

All indexes defined in model `Meta.indexes` and deployed via Django migrations:

| Model | Fields | Purpose |
|-------|--------|---------|
| Task | (organization, is_archived, status) | Task list/board filtering |
| Task | (organization, due_date) | Due date range queries |
| Task | (status, due_date) | Overdue/upcoming queries |
| Task | (-created_at) | Default ordering |
| TaskAssignment | (officer, task) | Officer assignment lookups |
| TaskAssignment | (task) | Task-based assignment queries |
| Notification | (recipient, is_read, -created_at) | Unread notification queries |
| Notification | (recipient, -created_at) | Notification listing |
| User | (organization, is_active, role) | Officer list by org and role |

The Task and TaskAssignment indexes already exist. The User index is new and requires a migration.

### 3. Caching Architecture

#### Cache Backend

File-based cache (`django.core.cache.backends.filebased.FileBasedCache`) — no infrastructure changes needed.

#### Cache Key Registry

| Key Pattern | TTL | Content | Invalidated By |
|-------------|-----|---------|----------------|
| `org_{org_id}_officers` | 60s | Officer queryset for filter dropdowns | Officer add/remove, role change |
| `notif_unread_{user_id}` | 30s | Integer count of unread notifications | Notification create, mark read |
| `approved_orgs_list` | 60s | List of approved Organization objects | Org status change |
| `dashboard_charts_{user_id}_{org_id}_{scope}` | 30s | Full chart response dict | Task create/update/delete |
| `reports_officers_{org_id}` | 300s | Officer list for reports filter | Officer add/remove |

#### Invalidation Strategy

```python
# In task save/delete signals or service layer:
from django.core.cache import cache

def invalidate_task_caches(task):
    """Invalidate caches affected by a task mutation."""
    org_id = task.organization_id
    if org_id:
        cache.delete(f'org_{org_id}_officers')
    # Invalidate notification caches for assigned officers
    for user_id in task.assigned_officers.values_list('id', flat=True):
        cache.delete(f'notif_unread_{user_id}')
    # Invalidate dashboard chart caches (pattern-based deletion)
    # File-based cache doesn't support pattern delete, so use versioning or explicit keys
    cache.delete(f'dashboard_charts_{task.created_by_id}_{org_id}_all')
    cache.delete(f'dashboard_charts_{task.created_by_id}_{org_id}_my_tasks')
```

#### Cache Miss Handling

All cache reads follow this pattern:

```python
value = cache.get(cache_key)
if value is None:
    value = expensive_query()
    cache.set(cache_key, value, ttl)
return value
```

No exceptions are raised on cache miss — the system always falls back to a fresh query.

### 4. Static File Pipeline

#### Configuration

```python
# settings.py (production)
STORAGES = {
    "default": {"BACKEND": "core.storage.SmartMediaCloudinaryStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

WHITENOISE_MAX_AGE = 31536000  # 1 year for hashed files
```

#### Requirements Addition

Add `Brotli` to `requirements.txt` to enable Brotli pre-compression during `collectstatic`:

```
Brotli==1.1.0
```

WhiteNoise automatically detects the Brotli library and generates `.br` files alongside `.gz` files during `collectstatic`. At request time, it serves the best available encoding based on `Accept-Encoding`.

#### Font CORS

WhiteNoise's `CompressedManifestStaticFilesStorage` handles CORS headers for font files automatically when `WHITENOISE_ALLOW_ALL_ORIGINS = True` (default behavior for font extensions).

### 5. API Response Optimization

#### Field Limiting

```python
class TaskListAPIView(APIView):
    def get(self, request):
        # ... queryset building ...
        data = list(tasks.values(
            'id', 'task_number', 'title', 'status',
            'priority', 'progress', 'due_date'
        )[:50])
        response = Response(data)
        response['Cache-Control'] = 'private, max-age=0'
        return response
```

#### Cache-Control Headers

| Endpoint Type | Header Value |
|--------------|-------------|
| User-specific (TaskList, Notifications) | `private, max-age=0` |
| Aggregated (DashboardStats, DashboardCharts) | `private, max-age=30` |

### 6. Connection Persistence

```python
# Already configured via dj_database_url.parse():
DATABASES = {
    'default': dj_database_url.parse(
        NEON_DB_URL,
        conn_max_age=600,
        conn_health_checks=True
    )
}
```

The current settings already configure `conn_max_age=600` and `conn_health_checks=True`. No changes needed — this design documents the existing correct configuration and ensures it is not accidentally removed.

With Render free tier running 1 gunicorn worker (or 2 max), total connections = workers × 1 = 1-2, well within Neon's free-tier limit.

### 7. Template Rendering Patterns

#### Pre-computed Context

Views compute all data before passing to templates. Templates never call methods that trigger queries:

```python
# GOOD - in view
ctx['can_edit'] = request.user.can_edit_task(task)  # uses prefetch cache
ctx['officer_count'] = task.assigned_officers_count  # uses prefetch cache

# BAD - in template
# {{ task.assigned_officers.filter(role='executive').count }}
```

#### Zero-Query Template Rendering

The task list already uses `select_related` and `prefetch_related`. The design ensures all new views follow this pattern — particularly the Kanban board (which currently issues per-column queries) and the calendar events view.

### 8. Permission Check Optimization

#### Prefetch-Aware Membership Check

```python
def can_edit_task(self, task):
    if self.has_task_override:
        return True
    if task.created_by_id == self.id:
        return True
    # Use prefetch cache if available (all() hits cache, not DB)
    if hasattr(task, '_prefetched_objects_cache') and 'assigned_officers' in task._prefetched_objects_cache:
        return any(u.id == self.id for u in task.assigned_officers.all())
    # Fallback to efficient exists() query
    return task.assigned_officers.filter(id=self.id).exists()
```

#### Request-Level Organization Caching

The `get_organization` method already caches on `request._cached_org`. This design ensures all permission checks that need the organization use this cached value rather than traversing the FK again.

### 9. Export Batching

For exports exceeding 500 tasks:

```python
def export_large_queryset(qs):
    """Process large querysets in chunks to limit memory."""
    if qs.count() > 500:
        for task in qs.iterator(chunk_size=200):
            yield task
    else:
        yield from qs
```

The PDF and Excel export views will use `iterator(chunk_size=200)` for large exports, building the output incrementally rather than loading all task objects into memory at once.

### 10. GZip Response Compression

Django's `GZipMiddleware` compresses HTML and JSON responses exceeding 200 bytes when the client sends `Accept-Encoding: gzip`. It does not compress:
- Streaming responses
- File downloads (PDF, Excel)
- Responses smaller than 200 bytes

Positioned after SecurityMiddleware (to ensure security headers are set) and before WhiteNoiseMiddleware (which handles its own compression for static files).

## Data Models

No new models are introduced. Changes are limited to:

1. **New index on User model**: `(organization, is_active, role)` via `Meta.indexes` addition
2. **Migration**: One new migration in the `accounts` app for the User index

```python
# accounts/models.py - Meta addition
class User(AbstractUser):
    # ... existing fields ...
    class Meta:
        indexes = [
            models.Index(fields=['organization', 'is_active', 'role']),
        ]
```

All other indexes already exist in the Task and Notification models.

=======
graph TB
    subgraph "Client Layer"
        Browser[Browser]
    end

    subgraph "Edge / CDN"
        CDN[cdn.jsdelivr.net<br/>Bootstrap CSS/JS]
    end

    subgraph "Render Platform"
        RP[Render Reverse Proxy<br/>keep-alive=5s]
    end

    subgraph "Application Server"
        GC[gunicorn.conf.py<br/>4 workers, gthread, 2 threads]
        WN[WhiteNoise<br/>CompressedManifest<br/>immutable cache]
        PM[PerformanceMiddleware<br/>DEBUG only]
        DT[Django Debug Toolbar<br/>DEBUG only]
        
        subgraph "Django Views"
            TV[Task Views<br/>optimized querysets]
            DV[Dashboard Views<br/>aggregate queries]
            MV[Monitoring View<br/>annotated queryset]
            RV[Reports View<br/>single aggregate]
            API[API Views<br/>conditional counts]
        end

        subgraph "Caching Layer"
            FC[File-Based Cache<br/>django_cache/]
            CP[Context Processors<br/>cached notification + org]
            VC[View-level Cache<br/>officers list, dashboard counts]
        end
    end

    subgraph "Database"
        PG[Neon PostgreSQL<br/>conn_max_age=600<br/>keepalives_idle=30<br/>connect_timeout=10]
        IDX[Composite Indexes<br/>Task, Notification,<br/>TaskAssignment, ActivityLog]
    end

    Browser --> CDN
    Browser --> RP
    RP --> GC
    GC --> WN
    GC --> PM
    GC --> TV & DV & MV & RV & API
    TV & DV & MV & RV & API --> FC
    TV & DV & MV & RV & API --> PG
    CP --> FC
    PG --- IDX
```

## Components and Interfaces

### 1. Query Optimizer Components

#### TaskBoardView Optimization
**Current:** Issues N queries (one per status column for tasks + one per status for count).  
**Optimized:** Single base queryset with `select_related`/`prefetch_related`, then Python-level grouping by status. Single aggregate `Count` query grouped by status.

```python
# core/query_utils.py
from django.db.models import Count, Q
from collections import defaultdict

def group_tasks_by_status(queryset, status_choices, limit_per_group=50):
    """
    Given a queryset of tasks with select_related/prefetch_related already applied,
    fetch all tasks and group them by status in Python.
    Returns dict[status_code] -> list[Task] (capped at limit_per_group).
    Also returns counts dict[status_code] -> int (full count per status).
    """
    # Single aggregate query for counts
    counts_qs = queryset.values('status').annotate(count=Count('id'))
    counts = {item['status']: item['count'] for item in counts_qs}
    
    # Fetch tasks grouped in-memory (limited per group)
    # Use a single queryset fetch with ordering, then slice in Python
    all_tasks = list(queryset.order_by('status', '-created_at'))
    grouped = defaultdict(list)
    for task in all_tasks:
        if len(grouped[task.status]) < limit_per_group:
            grouped[task.status].append(task)
    
    return grouped, counts
```

#### DashboardChartsAPIView Optimization
**Current:** Individual queries per status, per priority, per month (loop), per day (loop).  
**Optimized:** Conditional `Count` aggregates and `TruncMonth`/`TruncDate` grouping.

```python
# Optimized status + priority distribution (single query)
from django.db.models import Count, Q, Case, When, IntegerField
from django.db.models.functions import TruncMonth, TruncDate

def get_distributions(base_qs):
    """Single query for status + priority distributions."""
    agg_kwargs = {}
    for code, label in Task.STATUS_CHOICES:
        agg_kwargs[f'status_{code}'] = Count('id', filter=Q(status=code))
    for code, label in Task.PRIORITY_CHOICES:
        agg_kwargs[f'priority_{code}'] = Count('id', filter=Q(priority=code))
    return base_qs.aggregate(**agg_kwargs)


def get_monthly_completed(base_qs, start_date):
    """Single query for monthly completed tasks using TruncMonth."""
    return (
        base_qs
        .filter(status='completed', completion_date__gte=start_date)
        .annotate(month=TruncMonth('completion_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )


def get_weekly_trend(base_qs, start_date, end_date):
    """Single query for daily completed tasks over 7 days."""
    return (
        base_qs
        .filter(status='completed', completion_date__gte=start_date, completion_date__lte=end_date)
        .annotate(day=TruncDate('completion_date'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
```

#### DashboardStatsAPIView Optimization
**Current:** 4 separate count() calls.  
**Optimized:** Single aggregate with conditional Count.

```python
def get_dashboard_stats(base_qs, today):
    """Single aggregate query for all dashboard counts."""
    active_statuses = ['not_started', 'processing', 'to_advisers', 
                       'accounting', 'oca', 'osas', 'ppss', 'supply']
    return base_qs.aggregate(
        active=Count('id', filter=Q(status__in=active_statuses)),
        completed=Count('id', filter=Q(status='completed')),
        overdue=Count('id', filter=Q(due_date__lt=today) & Q(status__in=active_statuses)),
        upcoming=Count('id', filter=Q(
            due_date__gte=today,
            due_date__lte=today + timezone.timedelta(days=7),
            status__in=active_statuses
        )),
    )
```

#### ReportsDashboardView Optimization
**Current:** Calls `tasks.count()`, `active_tasks.count()`, `completed_tasks.count()` on overlapping querysets.  
**Optimized:** Single aggregate from the filtered queryset.

```python
def get_report_counts(tasks_qs, today):
    """Single aggregate for report summary stats."""
    return tasks_qs.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        active=Count('id', filter=~Q(status='completed')),
        overdue=Count('id', filter=Q(due_date__lt=today) & ~Q(status='completed')),
        in_progress=Count('id', filter=~Q(status__in=['not_started', 'completed'])),
    )
```

### 2. Performance Middleware

```python
# core/middleware.py
import time
import logging
from django.conf import settings
from django.db import connection

logger = logging.getLogger('csg.performance')

QUERY_COUNT_THRESHOLD = getattr(settings, 'PERF_QUERY_COUNT_THRESHOLD', 15)
REQUEST_DURATION_THRESHOLD_MS = getattr(settings, 'PERF_REQUEST_DURATION_THRESHOLD_MS', 2000)


class PerformanceMonitoringMiddleware:
    """
    Middleware that tracks query count and request duration.
    In DEBUG mode: adds X-Query-Count and X-Query-Time-Ms headers.
    Always: logs warnings when thresholds are exceeded.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        initial_queries = len(connection.queries)

        response = self.get_response(request)

        duration_ms = int((time.time() - start_time) * 1000)
        query_count = len(connection.queries) - initial_queries
        query_time_ms = int(sum(
            float(q.get('time', 0)) for q in connection.queries[initial_queries:]
        ) * 1000)

        # Log warnings for threshold violations
        if query_count > QUERY_COUNT_THRESHOLD:
            logger.warning(
                f"High query count: {request.path} executed {query_count} queries"
            )
        if duration_ms > REQUEST_DURATION_THRESHOLD_MS:
            logger.warning(
                f"Slow request: {request.path} took {duration_ms}ms"
            )

        # Add debug headers only in DEBUG mode
        if settings.DEBUG:
            response['X-Query-Count'] = str(query_count)
            response['X-Query-Time-Ms'] = str(query_time_ms)

        return response
```

### 3. Cache Invalidation Service

```python
# core/cache_utils.py
from django.core.cache import cache


def invalidate_task_caches(organization_id):
    """Invalidate all task-related caches for an organization."""
    cache.delete(f'officers_list_{organization_id}')
    # Dashboard count caches use pattern: dashboard_counts_{user_id}_{scope}
    # We cannot iterate all user keys with file cache, so we use a version key
    cache.delete(f'dashboard_version_{organization_id}')


def get_dashboard_cache_key(user_id, scope, org_id):
    """Generate versioned dashboard cache key."""
    version = cache.get(f'dashboard_version_{org_id}', 0)
    return f'dashboard_counts_{user_id}_{scope}_v{version}'


def invalidate_officers_cache(organization_id):
    """Invalidate officers list cache for an organization."""
    cache.delete(f'officers_list_{organization_id}')
    cache.delete('officers_list_all')


def invalidate_org_cache():
    """Invalidate approved organizations cache."""
    cache.delete('approved_orgs_list')
```

### 4. Bulk Operations Service

```python
# tasks/services.py (additions)
from django.db import transaction
from django.utils import timezone
from tasks.models import Task, TaskHistory, TaskAssignment
from notifications.models import Notification


def bulk_complete_tasks(queryset, user):
    """
    Mark multiple tasks as completed using bulk operations.
    Returns the count of updated tasks.
    
    Uses at most 3 write queries:
    - 1 bulk_update for task fields
    - 1 bulk_create for TaskHistory records
    - 1 bulk_create for Notification records
    """
    now_date = timezone.now().date()
    status_dict = dict(Task.STATUS_CHOICES)
    
    tasks_to_update = []
    history_records = []
    notification_records = []
    
    # Prefetch assignments for notification creation
    tasks = list(queryset.exclude(status='completed').prefetch_related('assignments__officer'))
    
    for task in tasks:
        old_status = task.status
        task.status = 'completed'
        task.completion_date = now_date
        task.progress = 100
        tasks_to_update.append(task)
        
        history_records.append(TaskHistory(
            task=task,
            changed_by=user,
            field_changed='Status',
            old_value=status_dict.get(old_status, old_status),
            new_value='Completed'
        ))
        
        for assignment in task.assignments.all():
            notification_records.append(Notification(
                recipient=assignment.officer,
                title='Task Completed',
                message=f'Task "{task.title}" has been marked as completed.',
                notification_type='task_completed',
                related_task=task
            ))
    
    with transaction.atomic():
        if tasks_to_update:
            Task.objects.bulk_update(
                tasks_to_update,
                fields=['status', 'completion_date', 'progress']
            )
        if history_records:
            TaskHistory.objects.bulk_create(history_records)
        if notification_records:
            Notification.objects.bulk_create(notification_records)
    
    return len(tasks_to_update)


def bulk_reassign_officers(task, new_officers, assigned_by):
    """
    Reassign officers to a task using bulk operations.
    Single delete + bulk_create within a transaction.
    """
    with transaction.atomic():
        TaskAssignment.objects.filter(task=task).delete()
        assignments = [
            TaskAssignment(task=task, officer=officer, assigned_by=assigned_by)
            for officer in new_officers
        ]
        if assignments:
            TaskAssignment.objects.bulk_create(assignments)
```

### 5. Gunicorn Configuration

```python
# gunicorn.conf.py (project root)
import multiprocessing
import os

# Worker configuration
worker_class = 'gthread'
workers = int(os.environ.get('WEB_CONCURRENCY', 4))
threads = 2
timeout = 120
keepalive = 5

# Worker recycling to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Bind
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
```

### 6. WhiteNoise / Static Asset Configuration

```python
# Settings additions (csg_project/settings.py)

# WhiteNoise configuration
WHITENOISE_MAX_AGE = 31536000  # 365 days for hashed files
WHITENOISE_ALLOW_ALL_ORIGINS = True  # CORS for static assets

# Storage backend selection
if not DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "core.storage.SmartMediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "core.storage.SmartMediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
```

### 7. Database Connection Configuration

```python
# Enhanced database configuration
DATABASES = {
    'default': dj_database_url.parse(
        NEON_DB_URL,
        ssl_require=not ('localhost' in NEON_DB_URL or '127.0.0.1' in NEON_DB_URL),
        conn_max_age=600,
        conn_health_checks=True,
    )
}
DATABASES['default'].setdefault('OPTIONS', {})
DATABASES['default']['OPTIONS'].update({
    'connect_timeout': 10,
    'keepalives_idle': 30,
})
```

### 8. Database Index Additions

New indexes to be added via migrations:

| Model | Index Fields | Purpose |
|-------|-------------|---------|
| Task | `(organization_id, is_archived, status)` | Already exists ✓ |
| Task | `(organization_id, due_date)` | Already exists ✓ |
| TaskAssignment | `(officer_id, task_id)` | Already exists ✓ |
| Notification | `(recipient_id, is_read, -created_at)` | Already exists ✓ |
| ActivityLog | `(organization_id, -timestamp)` | Already exists ✓ |

**Note:** After reviewing the current model Meta definitions, all required indexes already exist. No new migrations are needed for index additions. The existing indexes cover:
- Task: `(organization, status, is_archived)`, `(organization, due_date)`, `(status, due_date)`, `(-created_at)`
- TaskAssignment: `(officer, task)`, `(task,)`
- Notification: `(recipient, is_read, -created_at)`, `(recipient, -created_at)`
- ActivityLog: `(-timestamp)`, `(organization, -timestamp)`, `(action, -timestamp)`

## Data Models

No new models are introduced. The optimization modifies how existing models are queried and cached.

### Cache Key Schema

| Cache Key Pattern | TTL | Scope | Invalidation Trigger |
|---|---|---|---|
| `notif_unread_{user_id}` | 30s | Per-user | Notification create/update/delete |
| `officers_list_{org_pk}` | 60s | Per-org | Officer create/update/delete |
| `officers_list_all` | 60s | Global (super admin) | Officer create/update/delete |
| `approved_orgs_list` | 60s | Global (super admin) | Organization status change |
| `dashboard_counts_{user_id}_{scope}_v{version}` | 30s | Per-user, per-scope | Task create/update/delete (via version bump) |
| `dashboard_version_{org_id}` | None | Per-org | Task create/update/delete |

### Configuration Constants

```python
# settings.py additions
PERF_QUERY_COUNT_THRESHOLD = 15    # Warn if request exceeds this query count
PERF_REQUEST_DURATION_THRESHOLD_MS = 2000  # Warn if request exceeds this duration
```

>>>>>>> fix/optimization
## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

<<<<<<< HEAD
### Property 1: Conditional Aggregation Equivalence

*For any* set of tasks with arbitrary status values drawn from the 9 defined statuses, computing counts via a single `aggregate()` with conditional `Count` expressions SHALL produce identical results to computing each count via separate filtered `.count()` queries.

**Validates: Requirements 1.1, 1.3, 3.1, 12.1**

### Property 2: TruncMonth Aggregation Correctness

*For any* set of completed tasks with arbitrary completion dates spanning multiple months, a single query using `TruncMonth` annotation with `Count` SHALL produce per-month counts identical to individually filtering tasks by each month and counting.

**Validates: Requirements 1.4**

### Property 3: Status Partitioning with Limit and Ordering

*For any* list of tasks with arbitrary statuses and created_at timestamps, partitioning by status into groups (excluding 'completed'), limiting each group to 50 items ordered by created_at descending, SHALL produce: (a) correct membership (each task in the group matching its status), (b) correct count equal to the untruncated group size, (c) at most 50 items per group, (d) descending created_at ordering within each group, and (e) an entry for every defined non-completed status even if empty.

**Validates: Requirements 2.2, 2.3, 2.4, 2.5, 11.2**

### Property 4: N+1 Query Elimination Invariant

*For any* optimized API endpoint, the total number of database queries executed when returning N result objects SHALL equal the number of queries executed when returning 1 result object, for all N between 1 and 50.

**Validates: Requirements 3.6**

### Property 5: Cache Round-Trip Correctness

*For any* cacheable computation (officer list, notification count, chart data, approved orgs), after the initial computation stores the result in cache with a key, a subsequent cache get within the TTL SHALL return a value equal to the original computation result.

**Validates: Requirements 5.1, 5.2, 5.3, 5.5, 12.3**

### Property 6: Cache Invalidation on Mutation

*For any* task mutation (create, update, delete, status change), the cache keys for the task's organization officer list (`org_{org_id}_officers`) and the notification count keys for all assigned users (`notif_unread_{user_id}`) SHALL be deleted from the cache immediately after the mutation completes.

**Validates: Requirements 5.4**

### Property 7: Cache Miss Graceful Fallback

*For any* cache key that returns None (cache miss or cache failure), the system SHALL execute a fresh database query and return the correct result without raising an exception to the caller.

**Validates: Requirements 5.6**

### Property 8: API Response Field Limiting

*For any* task returned by TaskListAPIView, the response object SHALL contain exactly the keys {id, task_number, title, status, priority, progress, due_date} and no others. *For any* notification returned by UnreadNotificationsAPIView, the response object SHALL contain exactly the keys {id, title, message, type, created_at} and no others.

**Validates: Requirements 8.1, 8.4**

### Property 9: API Response List Bounding

*For any* number of matching records in the database, TaskListAPIView SHALL return at most 50 objects and UnreadNotificationsAPIView SHALL return at most 10 objects.

**Validates: Requirements 8.2, 8.4**

### Property 10: Chart Data Structural Invariant

*For any* chart dataset returned by DashboardChartsAPIView, each dataset object SHALL contain a "labels" array and a "data" array of equal length.

**Validates: Requirements 8.3**

### Property 11: Pagination Produces Bounded Results

*For any* page number and page size configuration in TaskListView, the evaluated queryset for the current page SHALL contain at most `page_size` records, and the SQL generated SHALL include LIMIT and OFFSET clauses.

**Validates: Requirements 11.1**

### Property 12: Top-N Aggregation Correctness

*For any* set of task assignments across M officers (M > 8), the top-8 query using annotated Count with ORDER BY descending and LIMIT 8 SHALL return exactly the 8 officers with the highest task counts, in descending order.

**Validates: Requirements 1.5, 11.3**

### Property 13: Export Batching Equivalence

*For any* queryset of N tasks (N > 500), processing via `iterator(chunk_size=200)` SHALL yield all N tasks in the same order as full queryset evaluation, with no duplicates or omissions.

**Validates: Requirements 12.4, 12.5**

### Property 14: Prefetch-Aware Permission Check

*For any* task with a prefetched `assigned_officers` cache, calling `can_edit_task(task)` or `can_update_task_progress(task)` SHALL return the same boolean result as when using a fresh `.filter(id=user_id).exists()` query, without issuing an additional database query.

**Validates: Requirements 13.1**

### Property 15: Request-Level Organization Caching

*For any* request where `get_organization()` is called multiple times, the second and subsequent calls SHALL return the same Organization instance as the first call without executing additional database queries.

**Validates: Requirements 13.2, 13.5**

### Property 16: Context Processor Zero-Query on Cache Hit

*For any* request where the notification count and approved organizations list are present in cache, the respective context processors SHALL execute zero database queries and return the cached values.

**Validates: Requirements 9.2**

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Cache read failure (file corruption, disk full) | Fall back to fresh DB query; log at DEBUG level |
| Database connection health check failure | Django closes stale connection, opens new one transparently |
| Database connection cannot be established | Django's `OperationalError` propagates to 500 handler |
| Export queryset exceeds memory during iteration | `iterator(chunk_size=200)` prevents full materialization |
| Static file not found in manifest | WhiteNoise returns 404; no crash |
| Cache TTL expires during request processing | Subsequent reads re-compute; no stale data served |

## Testing Strategy

### Property-Based Tests (using Hypothesis)

The project will use **Hypothesis** (Python property-based testing library) for correctness properties. Each property test runs a minimum of 100 iterations with generated inputs.

Configuration in `conftest.py`:
```python
from hypothesis import settings as hyp_settings
hyp_settings.register_profile("ci", max_examples=100)
hyp_settings.load_profile("ci")
```

Each property test is tagged with a comment referencing the design property:
```python
# Feature: performance-optimization, Property 1: Conditional aggregation equivalence
```

Tests to implement:
- **Property 1-3, 10, 12**: Pure function tests validating aggregation logic, partitioning, and structural invariants
- **Property 4**: Django TestCase with `assertNumQueries` comparing query counts at different result sizes
- **Property 5-7, 15-16**: Cache behavior tests using Django's cache framework with override settings
- **Property 8-9, 11**: API response structure tests with generated task data
- **Property 13**: Iterator equivalence test with large generated datasets
- **Property 14**: Permission check with/without prefetch cache comparison

### Unit Tests (example-based)

- Middleware ordering verification (MIDDLEWARE list position checks)
- Index existence verification (inspect `Meta.indexes` on each model)
- Configuration checks (CONN_MAX_AGE, cache backend, storage backend)
- Cache-Control header values on specific endpoints
- `check_org_admin_password` limit of 10 admin users

### Integration Tests

- Full dashboard page load with `assertNumQueries` ≤ 6
- Kanban board load with `assertNumQueries` ≤ 4
- Reports page response time under 2 seconds with 5000 tasks
- Static file response includes correct Content-Encoding and Cache-Control headers
- GZip compression applied to HTML responses > 200 bytes
- File download responses (PDF, Excel) not gzipped
=======
### Property 1: Query Optimization Equivalence

*For any* set of tasks in a tenant's dataset and any combination of filter parameters (status, priority, date range, officer assignment), the optimized aggregate query functions (get_distributions, get_monthly_completed, get_weekly_trend, get_dashboard_stats, get_report_counts) SHALL produce output identical to computing the same values via individual filtered count() calls on the same base queryset.

**Validates: Requirements 2.8**

### Property 2: Cache-Database Equivalence

*For any* authenticated request where cached data is served, the cached response content SHALL be semantically equivalent to the response that would be generated by querying the database directly with the same user, organization, and request parameters.

**Validates: Requirements 13.5**

### Property 3: Cache Tenant Isolation

*For any* two users belonging to different organizations, the set of cache keys accessible to user A and the set of cache keys accessible to user B SHALL have zero intersection for organization-scoped data (officers list, dashboard counts, task data). Every organization-scoped cache key SHALL contain the organization identifier as a component.

**Validates: Requirements 7.6, 13.4**

### Property 4: View-Level Tenant Isolation Preservation

*For any* user and organization pair, the set of task records returned by any optimized view (Task_List_View, Task_Board_View, Report_View, Monitoring_View, DashboardChartsAPIView, DashboardStatsAPIView) SHALL be identical to the set returned by the original un-optimized view for the same user and organization context.

**Validates: Requirements 13.2**

### Property 5: Fragment Extraction Correctness

*For any* HTML string containing FRAGMENT_START and FRAGMENT_END markers, the FragmentResponseMixin SHALL return exactly the content between FRAGMENT_START and FRAGMENT_END (plus any content between FRAGMENT_SCRIPTS_START and FRAGMENT_SCRIPTS_END), and SHALL NOT include any content outside those markers (sidebar, topbar, modal HTML).

**Validates: Requirements 10.1**

### Property 6: Pagination Filter Preservation

*For any* combination of active filter and sort parameters (q, status, priority, category, officer, sort, scope) applied to a paginated view, the pagination links for all pages SHALL preserve every filter parameter exactly as submitted in the original request, such that navigating to page N and back to page 1 yields the same filtered result set.

**Validates: Requirements 11.7**

### Property 7: Bulk Operation Bounded Queries

*For any* number of tasks N (where 1 ≤ N ≤ 50), performing a bulk complete operation SHALL execute at most 3 database write queries (one bulk_update for tasks, one bulk_create for history, one bulk_create for notifications), regardless of N.

**Validates: Requirements 14.7**

### Property 8: Cache Invalidation on Mutation

*For any* task create, update, or delete operation within an organization, the cache keys for that organization's officers list and dashboard counts SHALL be invalidated within the same request-response cycle, such that the immediately subsequent request returns fresh data reflecting the mutation.

**Validates: Requirements 7.4, 13.6**



## Error Handling

### Cache Failures

| Scenario | Handling | User Impact |
|----------|----------|-------------|
| Cache read returns None (miss) | Query database, populate cache | None — transparent |
| Cache backend unavailable (FileNotFoundError, IOError) | Catch exception, query database directly | None — slight latency increase |
| Cache write fails | Log warning, continue without caching | None — next request will also miss |
| Corrupt cache data (unpickling error) | Catch exception, delete key, query database | None — self-healing |

```python
# Pattern for graceful cache fallback
from django.core.cache import cache
import logging

logger = logging.getLogger('csg.performance')

def safe_cache_get(key, fallback_fn, timeout=60):
    """
    Attempt cache read; on any failure, execute fallback_fn and cache result.
    Never raises to caller — always returns valid data.
    """
    try:
        value = cache.get(key)
        if value is not None:
            return value
    except Exception as e:
        logger.warning(f"Cache read failed for key={key}: {e}")
    
    value = fallback_fn()
    
    try:
        cache.set(key, value, timeout)
    except Exception as e:
        logger.warning(f"Cache write failed for key={key}: {e}")
    
    return value
```

### Database Connection Failures

| Scenario | Handling | User Impact |
|----------|----------|-------------|
| connect_timeout exceeded (10s) | Retry once with same timeout | Brief delay (up to 20s total) |
| Retry also fails | Return HTTP 503 with friendly error page | User sees "temporarily unavailable" |
| Connection dropped mid-request | Django auto-reconnects on next query (CONN_HEALTH_CHECKS) | None for subsequent queries |
| Neon idle disconnect | keepalives_idle=30s prevents premature drops; health check validates before reuse | None |

```python
# Database retry middleware (simplified)
from django.db import OperationalError
from django.http import HttpResponse

class DatabaseRetryMiddleware:
    """Retry database connection failures once before returning 503."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except OperationalError as e:
            if 'connect_timeout' in str(e) or 'connection' in str(e).lower():
                try:
                    from django.db import connection
                    connection.close()
                    return self.get_response(request)
                except OperationalError:
                    return HttpResponse(
                        'Database temporarily unavailable. Please try again.',
                        status=503,
                        content_type='text/plain'
                    )
            raise
```

### Bulk Operation Failures

| Scenario | Handling | User Impact |
|----------|----------|-------------|
| bulk_update/bulk_create raises IntegrityError | transaction.atomic() rolls back all changes | Error message: "Operation did not complete" |
| Partial failure mid-batch | Same — full rollback within atomic block | No partial state visible |
| Task count exceeds 50 limit | Reject request before processing, return error message | Warning: "Maximum 50 tasks per bulk operation" |

### Performance Threshold Violations

| Scenario | Handling | User Impact |
|----------|----------|-------------|
| Query count > 15 (configurable) | Log WARNING to csg.performance logger | None (developer visibility only) |
| Request duration > 2000ms (configurable) | Log WARNING to csg.performance logger | None (developer visibility only) |
| Individual query > 100ms (DEBUG only) | Log WARNING via Django database logger | None (developer visibility only) |

## Testing Strategy

### Dual Testing Approach

This feature uses both unit/integration tests and property-based tests for comprehensive coverage.

**Property-Based Testing Library:** [Hypothesis](https://hypothesis.readthedocs.io/) (Python's standard PBT library for Django projects)

**Configuration:** Each property test runs a minimum of 100 iterations via Hypothesis settings.

### Property-Based Tests

Each correctness property maps to a single Hypothesis test:

| Property | Test Description | Key Generators |
|----------|-----------------|----------------|
| 1: Query Optimization Equivalence | Compare aggregate results vs naive loop results | Random task sets with varying statuses/priorities/dates |
| 2: Cache-Database Equivalence | Compare cached response vs fresh DB response | Random user/org/filter combinations |
| 3: Cache Tenant Isolation | Verify cache keys never collide across orgs | Random org ID pairs |
| 4: View-Level Tenant Isolation | Verify optimized views return same data as original | Random multi-tenant task datasets |
| 5: Fragment Extraction | Verify only marker-bounded content returned | Random HTML with markers at various positions |
| 6: Pagination Filter Preservation | Verify all params preserved in pagination URLs | Random filter parameter dicts |
| 7: Bulk Bounded Queries | Verify ≤3 writes for any task count 1-50 | Random integers 1-50 |
| 8: Cache Invalidation | Verify mutation invalidates correct cache keys | Random task CRUD sequences |

**Tag Format:** Each test is tagged with:
```python
# Feature: performance-optimization, Property {N}: {property_text}
```

### Integration Tests

| Area | Test Cases | Assertion Method |
|------|-----------|-----------------|
| Task List View queries | Warm cache, cold cache, with filters | `assertNumQueries(<=4)` |
| Board View queries | Multiple columns, varying task counts | `assertNumQueries` for single base query |
| Dashboard aggregate | Single vs multiple orgs | `assertNumQueries(1)` for counts |
| Charts API | Status, priority, monthly, weekly | `assertNumQueries` per section |
| Bulk complete | 1, 10, 50 tasks | `assertNumQueries(<=3)` for writes |
| Context processors | Cached vs uncached, authenticated vs anonymous | `assertNumQueries` |
| Fragment responses | With markers, without markers, scripts present | Response content inspection |
| Pagination | Page bounds, filter preservation, last page fallback | Status codes, URL params |

### Unit Tests (Example-Based)

| Component | Test Cases |
|-----------|-----------|
| `safe_cache_get` | Cache hit, cache miss, cache error, corrupt data |
| `invalidate_task_caches` | Correct keys deleted |
| `get_dashboard_cache_key` | Format includes user_id, scope, org_id, version |
| `group_tasks_by_status` | Empty queryset, single status, all statuses, >50 per group |
| `bulk_complete_tasks` | Zero tasks, one task, max tasks, already-completed tasks |
| `bulk_reassign_officers` | Empty list, single officer, multiple officers |
| Gunicorn config | Values match expected (workers=4, timeout=120, etc.) |
| WhiteNoise settings | DEBUG=True vs DEBUG=False storage backends |
| Performance middleware | Headers present in DEBUG, absent in production |

### Smoke Tests

| Check | Expected |
|-------|----------|
| All required indexes exist in migration state | Verified via `sqlmigrate` or Meta inspection |
| `brotli` in requirements.txt | Present with pinned version |
| `gunicorn.conf.py` exists at project root | File exists with correct values |
| WhiteNoise WHITENOISE_MAX_AGE = 31536000 | Setting value check |
| CONN_MAX_AGE = 600, connect_timeout = 10 | Settings check |
| Debug Toolbar not in INSTALLED_APPS when DEBUG=False | Conditional check |

### Test Execution

```bash
# Run all tests
python manage.py test

# Run property tests only (tagged)
python -m pytest tests/properties/ -v --hypothesis-show-statistics

# Run integration tests
python manage.py test --tag=performance

# Run with query logging for debugging
DEBUG=True python manage.py test --verbosity=2
```
>>>>>>> fix/optimization

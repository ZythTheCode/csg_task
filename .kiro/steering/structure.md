# Project Structure

```
CSG/
├── csg_project/          # Django project config (settings, urls, wsgi/asgi)
├── accounts/             # Custom User model, auth backends, login/profile views
├── core/                 # Dashboard, shared mixins, permissions, activity logging, storage
│   ├── management/commands/  # create_superadmin, seed_data, sync_media
│   ├── mixins.py         # FragmentResponseMixin for AJAX partial rendering
│   ├── permissions.py    # Tenant-scoped querysets, role mixins, DRF permissions
│   ├── storage.py        # Cloudinary smart storage backends
│   └── services/audit.py # Activity log service
├── tasks/                # Task CRUD, board, calendar, comments, attachments, exports
│   ├── api_urls.py       # DRF API routes (under /api/)
│   ├── api_views.py      # DRF viewsets/views
│   ├── urls.py           # Template-based view routes (under /tasks/)
│   └── templatetags/     # Custom filters (task_filters)
├── officers/             # Officer profiles, positions, CRUD
├── organizations/        # Multi-tenant org model, context processors, admin
├── notifications/        # In-app notification model, views, context processor
├── monitoring/           # System monitoring views
├── reports/              # Reporting dashboard, analytics
├── templates/            # Global Django templates (one folder per app + base.html)
│   └── skeletons/        # Loading skeleton partials for AJAX transitions
├── static/
│   ├── css/              # style.css, skeleton.css
│   ├── js/              # ajax-nav.js, lucide.min.js, progress-bar.js, table-sort.js
│   └── images/           # favicon and static assets
├── media/                # User-uploaded files (local dev only; Cloudinary in prod)
├── fixtures/             # JSON data fixtures
├── requirements.txt      # Python dependencies (pinned versions)
├── build.sh              # Production build script (Render)
├── manage.py             # Django CLI entry point
└── .env                  # Local environment variables (not committed)
```

## Architecture Patterns

- **Multi-tenant via Organization FK**: Most models have an `organization` foreign key. Queries are scoped using `TenantScopedQuerySetMixin` and `TenantObjectPermissionMixin` in `core/permissions.py`.
- **Class-based views** (CBVs) for all page views; DRF `APIView` for JSON endpoints.
- **FragmentResponseMixin**: Views inherit this mixin to support AJAX partial page loads. Templates use `<!-- FRAGMENT_START -->` / `<!-- FRAGMENT_END -->` markers to delimit the updatable region.
- **URL namespacing**: Each app uses `app_name` and namespaced URL patterns (e.g., `tasks:list`, `officers:detail`).
- **Role-based access**: Permissions enforced via `RoleRequiredMixin` and property checks on the User model (`is_super_admin`, `can_manage_tasks`, etc.).
- **Skeleton loading states**: `templates/skeletons/` contains placeholder HTML shown during AJAX transitions.

## Conventions

- Models define `STATUS_CHOICES`, `PRIORITY_CHOICES`, color maps, and icon maps as class-level constants.
- Auto-generated sequential identifiers (e.g., `task_number` as `YYYY-NNNN`).
- `select_related` / `prefetch_related` used on querysets to minimize N+1 queries.
- Database indexes added explicitly on frequently-filtered fields via `Meta.indexes`.
- Templates follow the pattern `templates/{app_name}/{view_name}.html`.
- Static JS has no build step — files are served directly.

# Product Overview

CSG (Central Student Government) Task Management and Monitoring System is a multi-tenant Django web application used by student government organizations to manage tasks, track officer assignments, and monitor organizational performance.

## Key Capabilities

- **Task Management**: Create, assign, track, and archive tasks with statuses, priorities, categories, due dates, comments, and file attachments. Tasks follow a multi-stage workflow (Not Started → Processing → To Advisers → Accounting → OCA → OSAS → PPSS → Supply → Completed).
- **Officer Management**: Track student government officers, their positions, and task workload.
- **Multi-Org Tenancy**: Multiple organizations share one deployment. Each org has its own tasks, officers, positions, and branding/theme. Super Admins can switch between organizations.
- **Notifications**: In-app notifications for task assignments, updates, comments, due dates, and system events.
- **Reports & Exports**: Dashboard analytics, PDF and Excel task exports.
- **Monitoring**: Activity logging and audit trail for compliance.
- **AJAX Navigation**: Single-page-app feel via fragment-based partial page updates without a JS framework.

## User Roles (highest to lowest privilege)

1. Super Admin — cross-org access, system-wide settings
2. Org Admin — manages a single organization
3. President — officer management + task override within their org
4. Elected Officer (Executive) — standard task operations
5. Committee Member — baseline task participation

## Deployment

Hosted on Render with Neon PostgreSQL (both production and local development). Media files stored via Cloudinary. Static files served by WhiteNoise.

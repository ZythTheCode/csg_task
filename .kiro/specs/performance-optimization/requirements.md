# Requirements Document

## Introduction

This specification defines performance optimizations for the CSG Task Management and Monitoring System — a multi-tenant Django web application deployed on Render with Neon PostgreSQL. The goal is to reduce page load times, minimize database round-trips, optimize frontend asset delivery, and improve perceived responsiveness without breaking any existing functionality (authentication, role-based access, task workflows, calendar, notifications, dark mode, AJAX navigation, exports, or multi-tenancy).

All optimizations follow the principle: Measure → Identify bottleneck → Make smallest safe change → Test → Measure again. Security and correctness take priority over performance at all times.

## Glossary

- **System**: The CSG Task Management and Monitoring System Django application
- **Query_Optimizer**: The component responsible for adding select_related/prefetch_related calls and restructuring ORM queries
- **Index_Manager**: The component responsible for adding or verifying database indexes on PostgreSQL
- **Cache_Layer**: The Django file-based cache backend and related caching logic
- **Asset_Pipeline**: The static file serving infrastructure (WhiteNoise, CDN references, CSS/JS files)
- **Fragment_Renderer**: The FragmentResponseMixin and AJAX navigation system that delivers partial page updates
- **Context_Processor**: Django context processors that execute on every authenticated request
- **Connection_Pool**: The database connection management layer (Django + Neon PostgreSQL)
- **Notification_Processor**: The notifications context processor that runs on every authenticated request
- **Organization_Processor**: The organizations context processor that runs on every authenticated request
- **Dashboard_View**: The main DashboardView that renders the landing page after login
- **Monitoring_View**: The MonitoringDashboardView that displays officer performance metrics
- **Task_List_View**: The TaskListView that renders the paginated task list
- **Task_Board_View**: The TaskBoardView that renders the Kanban board
- **Report_View**: The ReportsDashboardView that renders analytics and export options
- **API_Charts_View**: The DashboardChartsAPIView that returns chart data as JSON

## Requirements

### Requirement 1: Database Query Optimization for Task Views

**User Story:** As an officer, I want the task list, board, and calendar views to load quickly, so that I can manage my tasks without waiting for slow page loads.

#### Acceptance Criteria

1. WHEN the Task_List_View loads a page, THE Query_Optimizer SHALL ensure no more than 4 database queries are executed for the view's own logic (base queryset, pagination count, officers list cache check, and paginated result fetch), excluding queries issued by Context_Processor middleware
2. WHEN the Task_Board_View renders columns, THE Query_Optimizer SHALL retrieve all non-archived tasks for the board using a single base queryset with select_related and prefetch_related, then filter in-memory or via slicing per status column, rather than issuing independent unrelated querysets per column
3. WHEN the Task_Board_View counts tasks per column, THE Query_Optimizer SHALL use a single aggregated Count query grouped by status with conditional filters, instead of issuing one separate count query per status column
4. WHEN the TaskCalendarEventsView serializes tasks, THE Query_Optimizer SHALL prefetch assigned officer data (including officer_profile and position) so that iterating over assigned_officers for each task triggers zero additional database queries
5. WHEN the TaskDetailView loads a task, THE Query_Optimizer SHALL prefetch comments (with author), attachments, history (with changed_by), and assigned officers (with officer_profile and position) using select_related and prefetch_related, resulting in no more than 6 total queries for the detail page (task fetch, comments, attachments, history, assignments, and permission check), excluding Context_Processor queries
6. WHEN any task view (Task_List_View, Task_Board_View, TaskCalendarEventsView, or TaskDetailView) completes its database queries and renders the response, THE System SHALL return the full HTTP response within 2000 milliseconds under normal load (up to 500 tasks in the organization and up to 20 concurrent users)

### Requirement 2: Database Query Optimization for Dashboard and Monitoring

**User Story:** As an administrator, I want the dashboard and monitoring pages to load within acceptable time, so that I can quickly assess organization performance.

#### Acceptance Criteria

1. WHEN the Dashboard_View renders, THE Query_Optimizer SHALL use a single aggregate query for task counts (active, completed, overdue, upcoming) rather than issuing four separate count queries, resulting in exactly one database query for all four counts
2. WHEN the Monitoring_View loads officer data, THE Query_Optimizer SHALL retrieve all officer metrics (total tasks, completed tasks, active tasks, overdue tasks) in a single annotated queryset rather than calling per-officer methods, resulting in no more than one query for officer metric computation regardless of the number of officers
3. WHEN the API_Charts_View computes monthly completed tasks, THE Query_Optimizer SHALL use a single queryset with database-level date grouping (TruncMonth or equivalent) instead of issuing one query per month in a loop, resulting in exactly one database query regardless of the number of months displayed
4. WHEN the API_Charts_View computes weekly trend data, THE Query_Optimizer SHALL use a single queryset with database-level date grouping (TruncDate or equivalent) instead of issuing one query per day in a loop, resulting in exactly one database query for all 7 days of trend data
5. WHEN the Report_View renders, THE Query_Optimizer SHALL compute task_count, active_count, and completed_count from a single aggregate query or from the already-evaluated queryset length, rather than calling count() multiple times on overlapping filtered querysets
6. WHEN the API_Charts_View computes status distribution, THE Query_Optimizer SHALL use a single queryset grouped by status field rather than issuing one query per status value, resulting in exactly one database query regardless of the number of status choices
7. WHEN the API_Charts_View computes priority distribution, THE Query_Optimizer SHALL use a single queryset grouped by priority field rather than issuing one query per priority value, resulting in exactly one database query regardless of the number of priority choices
8. IF a query optimization is applied, THEN THE Query_Optimizer SHALL return results identical to the original un-optimized implementation, with no difference in the response data visible to the end user

### Requirement 3: Context Processor Optimization

**User Story:** As any authenticated user, I want every page request to be fast, so that navigation feels instant regardless of which page I visit.

#### Acceptance Criteria

1. IF the notification unread count cache key exists for the current user (cache is warm), THEN THE Notification_Processor SHALL return the cached integer value and execute zero database queries for the unread count
2. IF the notification unread count cache key does not exist for the current user (cache is cold), THEN THE Notification_Processor SHALL execute at most 2 database queries (one COUNT query for unread notifications, one SELECT query for the 5 most recent notifications) and store the unread count in cache with a timeout of 30 seconds
3. THE Organization_Processor SHALL cache the approved organizations list (id, name, and abbreviation fields only) with a cache timeout of 60 seconds, shared across all super admin users using a single cache key
4. WHEN a non-super-admin user requests a page, THE Organization_Processor SHALL return the user's organization from the already-loaded User instance FK attribute, executing zero additional database queries
5. THE Notification_Processor recent notifications query SHALL use only() to defer all fields except notification id, title, notification_type, is_read, created_at, and the related task id and task_number
6. IF the request user is not authenticated, THEN THE Notification_Processor and Organization_Processor SHALL each return immediately with empty default values and execute zero database queries

### Requirement 4: Database Index Verification and Addition

**User Story:** As a system administrator, I want database queries to use indexes effectively, so that query response times remain consistent as data grows.

#### Acceptance Criteria

1. WHEN the Index_Manager verifies the TaskAssignment model, THE Index_Manager SHALL confirm that a composite index exists on (officer_id, task_id) in that column order, and IF the index is missing, THEN THE Index_Manager SHALL add it via Django Meta.indexes to support officer-scoped task lookups
2. WHEN the Index_Manager verifies the Notification model, THE Index_Manager SHALL confirm that a composite index exists on (recipient_id, is_read, created_at DESC) in that column order, and IF the index is missing, THEN THE Index_Manager SHALL add it via Django Meta.indexes to support the notification context processor query that filters by recipient_id and is_read then orders by created_at descending
3. WHEN the Index_Manager verifies the Task model, THE Index_Manager SHALL confirm that a composite index exists on (organization_id, is_archived, status) in that column order, and IF the index is missing, THEN THE Index_Manager SHALL add it via Django Meta.indexes to support the filtered queryset pattern that filters by is_archived and organization before filtering by status
4. WHEN the Index_Manager verifies the ActivityLog model, THE Index_Manager SHALL confirm that a composite index exists on (organization_id, timestamp DESC) in that column order, and IF the index is missing, THEN THE Index_Manager SHALL add it via Django Meta.indexes to support the audit log display that filters by organization and orders by timestamp descending
5. IF a proposed index duplicates the leftmost prefix of an existing index on the same model, THEN THE Index_Manager SHALL skip adding the redundant index and SHALL include a code comment on the existing index entry stating which query pattern it already covers
6. WHEN the Index_Manager adds or confirms any index, THE Index_Manager SHALL not add more than one index per query pattern, and the total number of indexes per model SHALL not exceed 6 to limit write overhead on insert and update operations
7. IF the Index_Manager adds a new index to any model's Meta.indexes, THEN THE Index_Manager SHALL generate a corresponding Django migration file that creates the index without altering existing table data

### Requirement 5: Frontend Static Asset Optimization

**User Story:** As a user on a slow network, I want pages to load quickly by minimizing render-blocking resources, so that I can use the system even with limited bandwidth.

#### Acceptance Criteria

1. WHEN WhiteNoise's CompressedManifestStaticFilesStorage is configured as the staticfiles storage backend, THE Asset_Pipeline SHALL serve all static files with a Cache-Control header containing max-age of at least 31536000 seconds and the immutable directive
2. THE Asset_Pipeline SHALL configure WhiteNoise to serve pre-compressed gzip (.gz) and brotli (.br) versions of static files when the corresponding compressed file exists on disk
3. THE Asset_Pipeline SHALL load the Bootstrap CSS (version 5.3.2) and Bootstrap Icons CSS (version 1.11.3) from cdn.jsdelivr.net using version-pinned URLs that include the exact version number in the path
4. THE Asset_Pipeline SHALL load table-sort.js with the defer attribute so that it does not block HTML parsing or initial render
5. THE Asset_Pipeline SHALL inline the critical CSS for the navigation progress bar (#nav-progress) and chart-loading-overlay within a style element in the head, and SHALL NOT include any render-blocking custom CSS link elements in the head beyond style.css and skeleton.css
6. IF CompressedManifestStaticFilesStorage is enabled, THEN THE Asset_Pipeline SHALL append a content-based hash to static file URLs so that cache-busted filenames change when file content changes

### Requirement 6: WhiteNoise and Static File Configuration

**User Story:** As a developer deploying on Render, I want static files to be served with optimal compression and caching, so that repeat visits are instant and bandwidth is minimized.

#### Acceptance Criteria

1. WHILE DEBUG is set to False, THE Asset_Pipeline SHALL use WhiteNoise's CompressedManifestStaticFilesStorage as the STORAGES["staticfiles"]["BACKEND"] in csg_project/settings.py
2. THE Asset_Pipeline SHALL set WHITENOISE_MAX_AGE to 31536000 (365 days in seconds) so that hashed static files are served with a Cache-Control max-age of 31536000
3. THE Asset_Pipeline SHALL set WHITENOISE_ALLOW_ALL_ORIGINS to True so that static assets return Access-Control-Allow-Origin headers permitting cross-origin requests
4. WHEN the build.sh script executes collectstatic, THE Asset_Pipeline SHALL produce pre-compressed .gz and .br variants alongside each static file in the staticfiles output directory
5. THE Asset_Pipeline SHALL include the Brotli Python package (brotli) as a pinned dependency in requirements.txt to enable WhiteNoise Brotli pre-compression support
6. WHILE DEBUG is set to True, THE Asset_Pipeline SHALL use Django's default StaticFilesStorage as the STORAGES["staticfiles"]["BACKEND"] so that development serves uncompressed files without manifest hashing

### Requirement 7: Django Caching Strategy Enhancement

**User Story:** As any user, I want frequently accessed data (officer lists, organization details, dashboard stats) to be served from cache, so that repeated page loads do not re-query the database.

#### Acceptance Criteria

1. THE Cache_Layer SHALL cache the officers list per organization with a TTL of 60 seconds and invalidate on officer create, update, or delete operations
2. THE Cache_Layer SHALL cache dashboard aggregate counts (active tasks, completed tasks, overdue tasks, upcoming tasks, total officers) per user and scope parameter with a TTL of 30 seconds
3. THE Cache_Layer SHALL cache the approved organizations list for super admin users with a TTL of 60 seconds and invalidate when an organization's status changes
4. WHEN a Task is created, updated, or deleted, THE Cache_Layer SHALL invalidate the officers list cache key and the dashboard counts cache keys for that task's organization
5. THE Cache_Layer SHALL use consistent cache key naming following the pattern: {resource}_{scope}_{identifier} (e.g., officers_list_{org_pk}, dashboard_counts_{user_id}_{scope})
6. THE Cache_Layer SHALL include the organization identifier in every cache key for organization-scoped data, ensuring that users in one organization never receive cached data belonging to another organization
7. IF the cache backend is unavailable or a cache read fails, THEN THE Cache_Layer SHALL fall back to querying the database directly without raising an error to the user

### Requirement 8: Database Connection Optimization for Neon PostgreSQL

**User Story:** As a developer, I want database connections to be managed efficiently on Neon's serverless PostgreSQL, so that connection overhead does not degrade response times.

#### Acceptance Criteria

1. THE Connection_Pool SHALL set CONN_MAX_AGE to 600 seconds to reuse connections across requests within Gunicorn workers
2. THE Connection_Pool SHALL enable CONN_HEALTH_CHECKS to validate connections before reuse, preventing errors from Neon's idle connection timeout
3. THE Connection_Pool SHALL configure the database OPTIONS with a connect_timeout of 10 seconds so that any new connection attempt that does not complete within 10 seconds is aborted and treated as a connection failure
4. IF a database connection attempt fails due to a connect_timeout expiration, THEN THE System SHALL retry the connection exactly once using the same 10-second connect_timeout, and IF the retry also fails, THEN THE System SHALL return an error response indicating that the database is temporarily unavailable
5. THE Connection_Pool SHALL set the Neon-specific keepalives_idle option to 30 seconds to prevent premature connection drops during idle periods shorter than 30 seconds
6. IF the DATABASE_URL refers to a remote host (not localhost or 127.0.0.1), THEN THE Connection_Pool SHALL enforce SSL-required mode for the database connection

### Requirement 9: API Endpoint Query Optimization

**User Story:** As a frontend component consuming API data, I want API responses to return quickly, so that chart rendering and real-time updates feel responsive.

#### Acceptance Criteria

1. WHEN the DashboardChartsAPIView is called, THE Query_Optimizer SHALL compute status distribution (across 9 status values) and priority distribution (across 4 priority values) in a single aggregate query using conditional Count expressions, resulting in no more than 1 database query for both distributions combined
2. WHEN the TaskListAPIView returns tasks, THE Query_Optimizer SHALL use select_related on the organization foreign key and only() limited to the fields: id, task_number, title, status, priority, progress, and due_date
3. WHEN the UnreadNotificationsAPIView is called, THE Query_Optimizer SHALL use select_related on related_task and only() to limit notification fields to: id, title, message, notification_type, created_at, and related_task_id
4. WHEN the DashboardStatsAPIView is called, THE Query_Optimizer SHALL compute active, completed, overdue, and upcoming counts in a single aggregate query with conditional Count expressions, resulting in exactly 1 database query instead of 4 separate count() calls
5. THE System SHALL set a Cache-Control header with max-age=15 on the DashboardChartsAPIView response to allow browser-level caching of chart data for 15 seconds
6. WHEN any optimized API endpoint (DashboardChartsAPIView, TaskListAPIView, UnreadNotificationsAPIView, DashboardStatsAPIView) is called, THE System SHALL return a JSON response within 500 milliseconds under normal operating conditions (fewer than 10,000 task records in the tenant's dataset)

### Requirement 10: Template and Rendering Optimization

**User Story:** As a user navigating the application, I want page transitions to be smooth and skeleton states to display instantly, so that the application feels responsive.

#### Acceptance Criteria

1. WHEN a fragment request is detected (X-Requested-With: XMLHttpRequest and X-Fragment: true headers present), THE Fragment_Renderer SHALL return only the HTML between FRAGMENT_START and FRAGMENT_END markers plus any content between FRAGMENT_SCRIPTS_START and FRAGMENT_SCRIPTS_END markers, excluding all sidebar, topbar, and modal HTML
2. IF FRAGMENT_START or FRAGMENT_END markers are not found in the rendered template, THEN THE Fragment_Renderer SHALL return the full rendered page response with X-Fragment-Response and X-Page-Title headers set (graceful degradation)
3. THE Fragment_Renderer SHALL set the Content-Length header on fragment responses to the byte length of the response body
4. WHEN rendering the task list template, THE System SHALL use prefetched related data (officer_profile and position via select_related/prefetch_related on the queryset) so that accessing assigned officer display names and position titles does not trigger additional database queries per row
5. THE System SHALL limit the Monitoring_View officer data to a maximum of 50 officers, sorted by completion rate descending, to cap template iteration count
6. WHEN a Kanban board column contains 50 tasks (the per-column maximum), THE System SHALL display a text indicator below the last task card showing the total task count for that status (e.g., "Showing 50 of {total_count}")

### Requirement 11: Pagination and Data Limiting

**User Story:** As a user viewing large datasets, I want data to be paginated consistently, so that pages load in constant time regardless of total data volume.

#### Acceptance Criteria

1. THE Task_List_View SHALL paginate results at 10 items per page and SHALL NOT return more than 10 task items in a single page response regardless of query parameters
2. THE NotificationListView SHALL paginate results at 20 items per page and SHALL NOT return more than 20 notification items in a single page response regardless of query parameters
3. WHEN the Report_View renders filtered tasks, THE System SHALL paginate the task list at 25 items per page and SHALL NOT load all matching tasks into the template context as a single unpaginated list
4. WHEN the ActivityLog is displayed, THE System SHALL paginate entries at 50 items per page and order results by timestamp descending
5. THE System SHALL ensure all paginated views obtain the total item count via a database COUNT query rather than loading all objects into application memory
6. IF a user requests a page number that exceeds the available pages, THEN THE System SHALL display the last available page of results instead of an error page
7. WHEN a paginated view is navigated to a subsequent page, THE System SHALL preserve all active filter and sort parameters in the pagination links

### Requirement 12: Performance Measurement Baseline

**User Story:** As a developer, I want to measure and track performance metrics, so that I can verify optimizations are effective and detect regressions.

#### Acceptance Criteria

1. IF DEBUG is True, THEN THE System SHALL include Django Debug Toolbar in INSTALLED_APPS and middleware to provide query count and timing visibility per request
2. WHEN any single request executes more database queries than the configurable threshold (default: 15, configured via Django settings), THEN THE System SHALL log a WARNING-level message to the `csg.performance` logger that includes the request path and the query count
3. WHEN any single request takes longer to complete than the configurable duration threshold (default: 2000ms, configured via Django settings), THEN THE System SHALL log a WARNING-level message to the `csg.performance` logger that includes the request path and the elapsed time in milliseconds
4. IF DEBUG is True, THEN THE System SHALL enable a custom middleware that adds `X-Query-Count` (integer) and `X-Query-Time-Ms` (integer, total query execution time in milliseconds) response headers to every HTTP response
5. IF DEBUG is True, THEN THE System SHALL enable database query logging at the WARNING level for queries exceeding 100ms execution time
6. IF DEBUG is False, THEN THE System SHALL NOT load Django Debug Toolbar or the performance response-header middleware, and SHALL NOT add the `X-Query-Count` or `X-Query-Time-Ms` headers to responses

### Requirement 13: Regression Prevention

**User Story:** As a developer, I want to ensure that performance optimizations do not break existing functionality, so that users experience the same correct behavior with better speed.

#### Acceptance Criteria

1. THE System SHALL maintain all existing URL patterns and view behaviors without modification to response content or status codes
2. THE System SHALL preserve all tenant isolation guarantees such that queries scoped via TenantScopedQuerySetMixin and TenantObjectPermissionMixin return the same result sets before and after optimization for a given user and organization context
3. THE System SHALL preserve all role-based access controls such that for any given user role and resource combination, permission checks (RoleRequiredMixin and User model property checks) produce the same allow or deny decision before and after optimization
4. THE System SHALL ensure that cached data respects tenant boundaries by including the organization identifier in all cache keys, so that no cache entry is retrievable by a user belonging to a different organization
5. WHEN cached data is served, THE System SHALL return a response that is semantically equivalent in content and status code to what the database query would return for the same user, organization, and request parameters
6. WHEN underlying data is created, updated, or deleted, THE System SHALL invalidate or update the corresponding cache entries within the same request-response cycle, so that subsequent requests reflect the current database state
7. IF the cache backend becomes unavailable or a cache read fails, THEN THE System SHALL fall back to serving the response directly from the database without returning an error to the user

### Requirement 14: Bulk Operation Optimization

**User Story:** As an administrator performing bulk actions (bulk delete, bulk complete), I want these operations to complete quickly, so that managing many tasks at once is practical.

#### Acceptance Criteria

1. WHEN TaskBulkCompleteView marks multiple tasks as completed, THE Query_Optimizer SHALL use bulk_update for the task status, progress, and completion_date fields instead of calling save() per task in a loop
2. WHEN TaskBulkCompleteView creates history entries for completed tasks, THE Query_Optimizer SHALL use bulk_create for all TaskHistory records in a single call instead of creating one per iteration
3. WHEN TaskBulkCompleteView creates notifications for assigned officers, THE Query_Optimizer SHALL use bulk_create for all Notification records in a single call instead of creating one per iteration
4. WHEN TaskUpdateView reassigns officers to a task, THE Query_Optimizer SHALL delete old TaskAssignment records in a single queryset delete call and create new TaskAssignment records using bulk_create instead of creating one per officer
5. THE System SHALL wrap each bulk operation (bulk complete, bulk delete, officer reassignment) in a single transaction.atomic() block so that either all records are committed or none are on failure
6. IF a bulk_create or bulk_update call fails within the transaction, THEN THE System SHALL roll back all changes made within that transaction and return an error message indicating the operation did not complete
7. WHEN performing bulk complete on a set of tasks, THE System SHALL complete the operation using at most 3 database write queries (one bulk_update for tasks, one bulk_create for history, one bulk_create for notifications) regardless of the number of tasks selected, up to a maximum of 50 tasks per request

### Requirement 15: Gunicorn and Render Deployment Optimization

**User Story:** As a system operator, I want the production deployment to be configured for optimal throughput, so that concurrent users experience consistent response times.

#### Acceptance Criteria

1. THE System SHALL configure Gunicorn with a worker count of 4 for the Render free-tier single-CPU instance, set via the WEB_CONCURRENCY environment variable or Gunicorn configuration file
2. THE System SHALL configure Gunicorn with a timeout of 120 seconds to accommodate report generation and export operations
3. THE System SHALL configure Gunicorn with the gthread worker class and 2 threads per worker to handle I/O-bound requests (database queries, Cloudinary calls) efficiently
4. THE System SHALL set Gunicorn's max-requests to 1000 with max-requests-jitter of 50 to prevent memory leaks from long-running worker processes
5. THE System SHALL configure keep-alive to 5 seconds to allow connection reuse between Render's reverse proxy and Gunicorn
6. THE System SHALL specify all Gunicorn parameters (worker class, timeout, threads, max-requests, max-requests-jitter, keep-alive) in the render.yaml startCommand or in a gunicorn.conf.py configuration file at the project root
7. IF Gunicorn fails to start with the configured parameters, THEN THE System SHALL exit with a non-zero status code so that Render marks the deployment as failed

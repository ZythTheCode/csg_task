# Requirements Document

## Introduction

This feature implements comprehensive backend and infrastructure performance optimizations for the CSG Task Management and Monitoring System. The application runs on Django 4.2 with PostgreSQL (Neon free tier), uses file-based caching, and serves static files via WhiteNoise. While a separate UI performance spec covers AJAX navigation and client-side loading states, this spec addresses server-side query optimization, database indexing, caching strategy, static asset delivery, API response efficiency, middleware streamlining, and template rendering performance — all within the constraints of the existing free-tier infrastructure (Render, Neon PostgreSQL, Cloudinary).

## Glossary

- **Query_Optimizer**: The server-side layer responsible for ensuring Django ORM queries use efficient patterns including select_related, prefetch_related, annotations, and conditional aggregations to minimize database round-trips.
- **Index_Manager**: The database indexing strategy ensuring frequently filtered, sorted, and joined columns have appropriate composite and single-column indexes for query plan efficiency.
- **Cache_Strategy**: The application-level caching layer that stores computed results in the file-based Django cache to avoid redundant database queries on repeated requests.
- **Static_Pipeline**: The static file serving and compression configuration using WhiteNoise that delivers CSS, JavaScript, and image assets with optimal compression, caching headers, and minimal overhead.
- **API_Optimizer**: The optimization layer for Django REST Framework endpoints that ensures serialization efficiency, queryset evaluation, and response payload minimization.
- **Middleware_Stack**: The ordered set of Django middleware classes processing every request/response cycle, where unnecessary processing is eliminated for improved throughput.
- **Template_Engine**: The Django template rendering system where template complexity, context processor overhead, and template fragment caching are optimized to reduce server-side render time.
- **Connection_Pool**: The database connection management configuration that reuses persistent connections to avoid TCP/SSL handshake overhead on every request to the Neon PostgreSQL instance.
- **Dashboard_View**: The main dashboard page that displays aggregated task statistics, recent tasks, and officer counts.
- **Task_List_View**: The paginated task listing page with filtering, sorting, and scope switching.
- **Kanban_Board_View**: The board-style task visualization showing tasks grouped by status columns.
- **Reports_View**: The analytics and reporting page that computes task statistics with various filters applied.
- **DashboardCharts_API**: The API endpoint that returns chart data including status distribution, priority distribution, monthly completions, tasks per officer, and weekly trends.

## Requirements

### Requirement 1: Database Query Consolidation for Dashboard

**User Story:** As an officer, I want the dashboard to load quickly, so that I can immediately see my task overview without waiting for multiple database queries.

#### Acceptance Criteria

1. WHEN the Dashboard_View computes task statistics, THE Query_Optimizer SHALL use a single aggregated query with conditional Count expressions for active, completed, overdue, and upcoming task counts rather than issuing separate count queries, where active statuses include not_started, processing, to_advisers, accounting, oca, osas, ppss, and supply.
2. WHEN the Dashboard_View loads recent tasks, THE Query_Optimizer SHALL retrieve at most 10 tasks using select_related for created_by and organization foreign keys and prefetch_related for assigned_officers with officer_profile and position in a single queryset chain.
3. WHEN the DashboardCharts_API computes chart data, THE Query_Optimizer SHALL use a single annotated queryset with conditional aggregation for status distribution across all 9 defined statuses and priority distribution across all 4 defined priorities rather than issuing one query per status or priority value.
4. WHEN the DashboardCharts_API computes monthly completion counts, THE Query_Optimizer SHALL use a single query with TruncMonth annotation and conditional aggregation covering the range from the configured start month up to the current month, rather than issuing one filtered count query per month.
5. WHEN the DashboardCharts_API computes tasks per officer, THE Query_Optimizer SHALL use a single annotated queryset with Count grouping ordered by count descending and limited to the top 8 officers, rather than iterating officers and counting tasks individually.
6. WHEN the Dashboard_View or DashboardCharts_API completes all database operations for a single page load, THE Query_Optimizer SHALL execute no more than 6 total database queries, and the combined query execution time SHALL be under 500 milliseconds for datasets of up to 10,000 tasks.

### Requirement 2: Kanban Board Single-Query Architecture

**User Story:** As an officer, I want the Kanban board to load in a single database round-trip, so that the board renders quickly even with many tasks across multiple status columns.

#### Acceptance Criteria

1. WHEN the Kanban_Board_View loads, THE Query_Optimizer SHALL fetch all non-archived tasks matching the current filters (scope, search query, category, priority, and officer) in a single queryset with select_related and prefetch_related applied, resulting in no more than 4 total database queries (1 main query plus up to 3 prefetch queries).
2. WHEN building status columns, THE Query_Optimizer SHALL partition the pre-fetched queryset into status groups using Python iteration rather than issuing a separate filtered database query per status column, excluding tasks with status "completed" from the board columns.
3. WHEN the Kanban_Board_View computes per-column task counts, THE Query_Optimizer SHALL derive counts from the pre-fetched queryset length for each status group rather than issuing additional COUNT queries to the database.
4. WHEN the Kanban_Board_View limits tasks per column to 50, THE Query_Optimizer SHALL apply the limit during Python partitioning after the single database fetch, selecting the first 50 tasks per column ordered by created_at descending, rather than using separate limited queries per column.
5. WHEN the pre-fetched queryset contains zero tasks for a status group, THE Query_Optimizer SHALL include that status column in the board output with a count of 0 and an empty task list.

### Requirement 3: N+1 Query Elimination in API Endpoints

**User Story:** As a developer, I want API endpoints to avoid N+1 query patterns, so that response times remain consistent regardless of the number of related objects.

#### Acceptance Criteria

1. WHEN the DashboardStatsAPIView computes task counts, THE Query_Optimizer SHALL use a single aggregate query with conditional Count expressions (active, completed, overdue, upcoming) rather than issuing four separate filtered count queries, resulting in no more than 2 database queries per request regardless of task count.
2. WHEN the TaskListAPIView iterates tasks to build response data and the response payload includes fields from related models, THE Query_Optimizer SHALL use select_related for ForeignKey relations and prefetch_related for ManyToMany relations on the queryset before iteration, ensuring total query count does not increase as the number of returned tasks increases.
3. WHEN the UnreadNotificationsAPIView fetches notifications, THE Query_Optimizer SHALL use select_related for the related_task ForeignKey and only() to limit retrieved columns to id, title, message, notification_type, and created_at, resulting in no more than 2 database queries regardless of notification count.
4. WHEN the TaskCalendarEventsView builds calendar event data, THE Query_Optimizer SHALL prefetch assigned_officers with officer_profile and position before iterating tasks, ensuring total query count does not increase as the number of tasks or assigned officers increases.
5. IF a new API endpoint is added that returns fields from related objects, THEN THE Query_Optimizer SHALL include select_related for ForeignKey traversals and prefetch_related for ManyToMany traversals such that the total number of database queries remains constant relative to the number of result objects returned.
6. WHEN verifying N+1 query elimination for any optimized endpoint, THE Query_Optimizer SHALL ensure that the total database query count for a request with 50 result objects is equal to the query count for a request with 1 result object.

### Requirement 4: Database Index Strategy

**User Story:** As a developer, I want database indexes to cover the most common query patterns, so that filtered and sorted queries execute efficiently on the Neon PostgreSQL free tier.

#### Acceptance Criteria

1. THE Index_Manager SHALL maintain a composite index on Task for (organization, is_archived, status) to support task listing queries that filter by organization scope, archive state, and status.
2. THE Index_Manager SHALL maintain a composite index on Task for (organization, due_date) to support due date filtering and sorting within an organization scope.
3. THE Index_Manager SHALL maintain a composite index on TaskAssignment for (officer, task) to support officer-task lookups used for task count queries and assignment existence checks.
4. THE Index_Manager SHALL maintain an index on Notification for (recipient, is_read, -created_at) to support unread notification count queries and reverse-chronological notification listing per user.
5. THE Index_Manager SHALL maintain an index on User for (organization, is_active, role) to support officer list queries that filter active users by organization and role.
6. WHEN a new queryset filter pattern is introduced that produces a sequential scan exceeding 1000 rows as determined by PostgreSQL EXPLAIN output, THE Index_Manager SHALL add a covering composite index via a Django migration, with field order matching the filter sequence used in the queryset.
7. THE Index_Manager SHALL define all composite indexes in the corresponding model's Meta.indexes list and generate a Django migration for each new or modified index.

### Requirement 5: Caching Strategy for Repeated Queries

**User Story:** As an officer, I want pages I visit frequently to respond faster on subsequent loads, so that navigating between dashboard and task list feels responsive.

#### Acceptance Criteria

1. WHEN the Task_List_View or Kanban_Board_View retrieves the officers list for filter dropdowns, THE Cache_Strategy SHALL cache the result per organization using cache key format "org_{org_id}_officers" with a TTL of 60 seconds using the file-based Django cache.
2. WHEN the notifications context processor computes the unread notification count, THE Cache_Strategy SHALL cache the count per user using cache key format "notif_unread_{user_id}" with a TTL of 30 seconds.
3. WHEN the organization context processor retrieves the approved organizations list for super admins, THE Cache_Strategy SHALL cache the result using cache key "approved_orgs_list" with a TTL of 60 seconds.
4. WHEN a task is created, updated, deleted, or its status is changed, THE Cache_Strategy SHALL invalidate the "org_{org_id}_officers" cache key for the task's organization AND invalidate the "notif_unread_{user_id}" cache key for all users assigned to that task.
5. WHEN the DashboardCharts_API computes chart data, THE Cache_Strategy SHALL cache the complete response using cache key format "dashboard_charts_{user_id}_{org_id}_{scope}" with a TTL of 30 seconds.
6. IF a cache read fails or returns None, THEN THE Cache_Strategy SHALL fall back to a fresh database query without raising an error to the user, and SHALL log the cache miss at DEBUG level.

### Requirement 6: Static File Compression and Caching Headers

**User Story:** As an officer on a slow network, I want static assets (CSS, JS, images) to be compressed and cached by my browser, so that pages load faster on repeat visits.

#### Acceptance Criteria

1. THE Static_Pipeline SHALL configure WhiteNoise with CompressedManifestStaticFilesStorage to serve pre-compressed gzip and Brotli versions of static files generated at collectstatic time.
2. THE Static_Pipeline SHALL set Cache-Control headers on static files to "public, max-age=31536000, immutable" for hashed filenames served by WhiteNoise.
3. IF cross-origin font files are served (files with extensions .woff, .woff2, .ttf, .eot), THEN THE Static_Pipeline SHALL set the Access-Control-Allow-Origin header to "*" on those responses.
4. WHEN a static file is requested and the client sends an Accept-Encoding header that includes "br", THE Static_Pipeline SHALL serve the Brotli-compressed version; IF the client only accepts "gzip", THEN THE Static_Pipeline SHALL serve the gzip-compressed version; otherwise THE Static_Pipeline SHALL serve the uncompressed version.
5. THE Static_Pipeline SHALL exclude files matching patterns "*.map" and "*.src.js" from the production static file manifest to reduce collectstatic output size.
6. THE Static_Pipeline SHALL add the Brotli Python library to requirements.txt to enable Brotli compression support in WhiteNoise.

### Requirement 7: Database Connection Persistence

**User Story:** As a developer, I want database connections to be reused across requests, so that the TCP and SSL handshake overhead to the Neon PostgreSQL instance does not add latency to every request.

#### Acceptance Criteria

1. THE Connection_Pool SHALL configure Django's CONN_MAX_AGE to 600 seconds so that each worker process reuses its database connection for up to 600 seconds before closing and re-establishing it.
2. THE Connection_Pool SHALL enable conn_health_checks so that Django verifies the connection is usable before executing a query on a reused connection.
3. IF a database connection health check fails, THEN THE Connection_Pool SHALL close the stale connection and establish a new connection within the same request cycle, returning the query result to the caller without surfacing a connection error.
4. IF a new connection cannot be established after a health check failure, THEN THE Connection_Pool SHALL allow Django's default database exception to propagate to the caller rather than silently dropping the request.
5. THE Connection_Pool SHALL maintain at most 1 database connection per worker process, ensuring the total concurrent connection count does not exceed the Neon free-tier limit when combined with the configured number of gunicorn workers.

### Requirement 8: API Response Payload Optimization

**User Story:** As a developer, I want API responses to contain only the data the frontend needs, so that response payloads are small and parsing is fast.

#### Acceptance Criteria

1. WHEN the TaskListAPIView returns task data, THE API_Optimizer SHALL include only the fields id, task_number, title, status, priority, progress, and due_date per task object, and SHALL exclude all other model fields from the serialized response.
2. WHEN the TaskListAPIView returns task data, THE API_Optimizer SHALL return a maximum of 50 task objects per response.
3. WHEN the DashboardChartsAPIView returns chart data, THE API_Optimizer SHALL structure each chart dataset as an object containing a "labels" array and a "data" array of equal length, ready for direct chart rendering without requiring client-side grouping, counting, or reshaping.
4. WHEN the UnreadNotificationsAPIView returns notifications, THE API_Optimizer SHALL include only the fields id, title, message, type, and created_at per notification object, and SHALL return a maximum of 10 notification objects per response.
5. THE API_Optimizer SHALL include a Cache-Control header of "private, max-age=0" on responses from user-specific endpoints (TaskListAPIView, UnreadNotificationsAPIView) and a Cache-Control header of "private, max-age=30" on responses from aggregated endpoints (DashboardStatsAPIView, DashboardChartsAPIView).

### Requirement 9: Template Rendering Optimization

**User Story:** As an officer, I want pages to render quickly on the server, so that initial page load and AJAX fragment responses are delivered with minimal delay.

#### Acceptance Criteria

1. WHEN the Task_List_View renders task rows, THE Template_Engine SHALL access only pre-fetched relationships (assigned_officers, officer_profile, position) and execute zero additional database queries per row during template rendering.
2. WHEN context processors execute on every request, THE Template_Engine SHALL ensure the notifications context processor (cache TTL of 30 seconds for unread count) and organization context processor (cache TTL of 60 seconds for approved organizations list) return cached values and execute zero database queries when cache hits occur.
3. WHEN rendering the Kanban board template, THE Template_Engine SHALL iterate pre-partitioned task lists per column (maximum 50 tasks per column) rather than filtering the full queryset within the template using template tags.
4. THE Template_Engine SHALL avoid calling model methods or properties that trigger database queries (such as assigned_officers.filter() or .exists() checks) inside template loops, using pre-computed annotations or prefetch caches instead.
5. IF a template tag or filter requires data that would necessitate a database query, THEN THE Template_Engine SHALL receive the pre-computed value via the view context rather than executing the query at render time.
6. WHEN any page renders with a typical dataset (up to 10 task rows in list view or up to 50 tasks per Kanban column), THE Template_Engine SHALL complete server-side template rendering in no more than 200 milliseconds excluding network latency.

### Requirement 10: Middleware Stack Optimization

**User Story:** As a developer, I want the middleware stack to process requests with minimal overhead, so that every request benefits from reduced per-request processing time.

#### Acceptance Criteria

1. THE Middleware_Stack SHALL order middleware such that SecurityMiddleware executes first and WhiteNoiseMiddleware executes second, before SessionMiddleware, AuthenticationMiddleware, and all other downstream middleware.
2. THE Middleware_Stack SHALL ensure WhiteNoise handles static file requests entirely within the middleware layer without invoking Django's URL routing, view resolution, or template systems.
3. WHEN a static file is served by WhiteNoise, THE Middleware_Stack SHALL not execute SessionMiddleware, AuthenticationMiddleware, MessageMiddleware, CsrfViewMiddleware, or any middleware positioned after WhiteNoiseMiddleware in the stack for that request.
4. IF DEBUG is False, THEN THE Middleware_Stack SHALL not include any debug-only or profiling middleware (such as django.contrib.admindocs middleware, debug toolbar middleware, or any middleware whose module path contains "debug" or "profiling").
5. IF additional middleware is introduced for performance monitoring, THEN THE Middleware_Stack SHALL ensure the middleware adds less than 1 millisecond of latency per request as measured at the 95th percentile under a load of 50 concurrent requests.

### Requirement 11: Pagination and Queryset Limiting

**User Story:** As an officer with many tasks, I want list views to load consistently fast regardless of total task count, so that performance does not degrade as the organization accumulates tasks over time.

#### Acceptance Criteria

1. WHEN the Task_List_View loads paginated results, THE Query_Optimizer SHALL apply ordering and filtering at the database level and retrieve only the current page's rows (default page size of 10) using LIMIT and OFFSET rather than fetching all matching rows and slicing in Python.
2. WHEN the Kanban_Board_View limits columns to 50 tasks each, THE Query_Optimizer SHALL evaluate the queryset lazily so that the database applies the LIMIT clause rather than transferring all matching rows to application memory.
3. WHEN the DashboardChartsAPIView computes tasks per officer, THE Query_Optimizer SHALL limit results to the top 8 officers by task count using database-level ORDER BY and LIMIT slicing.
4. WHEN the notification context processor loads recent notifications, THE Query_Optimizer SHALL use database-level LIMIT ([:5]) after applying filters (recipient, is_read) and ordering (-created_at).
5. THE Query_Optimizer SHALL ensure no view or API endpoint fetches an unbounded queryset (without pagination or explicit LIMIT) for display purposes, and any queryset evaluated for rendering SHALL have an explicit upper bound.

### Requirement 12: Reports View Query Efficiency

**User Story:** As a president or admin, I want the reports page to generate analytics quickly, so that I can review organization performance without long loading times.

#### Acceptance Criteria

1. WHEN the Reports_View computes summary statistics (total, completed, overdue, in_progress counts), THE Query_Optimizer SHALL retrieve all four counts in a single database query rather than issuing separate filtered count queries.
2. WHEN the Reports_View loads filtered tasks for display, THE Query_Optimizer SHALL apply all filters (officer, year, month, status, priority, scope) at the database level in a single queryset chain before evaluation, resulting in no more than 3 database queries for the page (task list, officer dropdown, and aggregate counts).
3. WHEN the Reports_View retrieves officers for the filter dropdown, THE Query_Optimizer SHALL use a cached officer list per organization with a cache time-to-live of 300 seconds, and SHALL invalidate the cache when an officer is added or removed from the organization.
4. WHEN generating PDF or Excel exports for a queryset exceeding 500 tasks, THE Query_Optimizer SHALL use iterator() with a chunk size of 200 records to avoid loading all task objects into memory simultaneously.
5. IF the export contains more than 500 tasks, THEN THE Query_Optimizer SHALL process tasks in batches of 200 records per batch to limit peak memory consumption.
6. WHEN the Reports_View page is requested, THE System SHALL return the fully rendered response within 2 seconds for datasets of up to 5000 tasks.

### Requirement 13: Efficient User Permission Checks

**User Story:** As a developer, I want permission checks to avoid redundant database queries, so that role and access verification does not add latency to every view dispatch.

#### Acceptance Criteria

1. WHEN the can_edit_task or can_update_task_progress methods check officer assignment, IF the task's assigned_officers queryset has been loaded via prefetch_related, THEN THE Query_Optimizer SHALL use the prefetched cache to determine membership without issuing a database query; IF the prefetch cache is not populated, THEN THE Query_Optimizer SHALL fall back to a single .filter(id=user_id).exists() query.
2. WHEN the User model's get_organization method is called during a request, THE Query_Optimizer SHALL store the resolved organization on the request object after the first database lookup so that all subsequent calls within the same request return the cached value without additional queries.
3. WHEN the TenantScopedQuerySetMixin filters by organization, THE Query_Optimizer SHALL access user.organization without triggering an additional SELECT query by ensuring the user object is loaded with select_related('organization') during authentication or session restoration.
4. THE Query_Optimizer SHALL ensure the check_org_admin_password function limits the admin users queryset to a maximum of 10 results, ordered by date_joined descending, to prevent unbounded iteration in organizations with many admins.
5. IF a permission check method (can_edit_task, can_update_task_progress, or check_org_admin_password) executes within a request that already resolved the user's organization, THEN THE Query_Optimizer SHALL reuse the cached organization value rather than triggering a redundant query on the organization foreign key.

### Requirement 14: GZip Response Compression

**User Story:** As an officer on a mobile network, I want HTML and JSON responses to be compressed, so that page loads consume less bandwidth and complete faster.

#### Acceptance Criteria

1. THE Middleware_Stack SHALL include Django's GZipMiddleware to compress responses with Content-Type text/html or application/json whose uncompressed body exceeds 200 bytes.
2. THE Middleware_Stack SHALL position GZipMiddleware after SecurityMiddleware and before WhiteNoiseMiddleware so that response compression applies to dynamically generated responses while WhiteNoise continues to serve static files independently.
3. WHEN a client sends an Accept-Encoding header that includes gzip, THE Middleware_Stack SHALL compress the qualifying response body and set the Content-Encoding: gzip header.
4. IF a client request does not include gzip in the Accept-Encoding header, THEN THE Middleware_Stack SHALL return the response uncompressed without the Content-Encoding header.
5. IF a response body is smaller than 200 bytes before compression, THEN THE Middleware_Stack SHALL serve the response uncompressed to avoid overhead exceeding the compression benefit.
6. THE Middleware_Stack SHALL not apply gzip compression to streaming responses or file download responses with Content-Type application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, or application/vnd.ms-excel.

### Requirement 15: Free-Tier Resource Constraints

**User Story:** As the system administrator, I want performance optimizations to operate within Render free-tier, Neon free-tier, and Cloudinary free-tier limits, so that the application remains deployable at zero cost.

#### Acceptance Criteria

1. THE Connection_Pool SHALL not open more than 5 simultaneous database connections per project, enforced via the Django DATABASES connection pool settings.
2. IF the database connection pool is exhausted (all 5 connections in use), THEN THE Connection_Pool SHALL queue the request and return a timeout error to the caller within 30 seconds rather than opening additional connections.
3. THE Cache_Strategy SHALL use the existing file-based Django cache (`django.core.cache.backends.filebased.FileBasedCache`) without introducing additional cache infrastructure (Redis, Memcached) that would require paid add-ons.
4. THE Static_Pipeline SHALL perform all compression and minification during the `collectstatic` build step rather than at request time, so that no on-the-fly compression middleware or libraries are invoked when serving responses.
5. THE Query_Optimizer SHALL ensure no single database query takes longer than 5 seconds when the database contains up to 10,000 task records across 20 organizations, verified using EXPLAIN ANALYZE on complex aggregation queries.
6. THE Cache_Strategy SHALL set cache TTLs between 30 and 60 seconds for data that changes on every user action (task status updates, new comments) and TTLs between 120 and 300 seconds for data that changes infrequently (positions, organization lists, role definitions).
7. THE API_Optimizer SHALL not introduce background task processing libraries (Celery, Django-Q, Huey) or additional worker processes; all request processing SHALL complete synchronously within the single Gunicorn web process allocated by the Render free tier.
8. THE Connection_Pool SHALL set `conn_max_age` to no more than 600 seconds to ensure idle connections are released back to Neon and do not count against the concurrent connection limit indefinitely.

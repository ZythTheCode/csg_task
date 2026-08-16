# Implementation Plan: Performance Optimization

## Overview

<<<<<<< HEAD
This implementation plan covers server-side performance optimization for the CSG Task Management System. Tasks are ordered by dependency: infrastructure/settings changes first, then database indexing, query optimization, caching, API optimization, middleware, template rendering, and finally testing. All changes operate within existing free-tier constraints (Render, Neon PostgreSQL, Cloudinary) with no new infrastructure.

## Tasks

- [x] 1. Infrastructure and settings configuration
  - [x] 1.1 Configure static file storage with CompressedManifestStaticFilesStorage
    - Update `STORAGES["staticfiles"]` in `csg_project/settings.py` to use `whitenoise.storage.CompressedManifestStaticFilesStorage`
    - Add `WHITENOISE_MAX_AGE = 31536000` setting for immutable caching headers on hashed files
    - Add `Brotli==1.1.0` to `requirements.txt` to enable Brotli pre-compression during collectstatic
    - _Requirements: 6.1, 6.2, 6.4, 6.6, 15.4_

  - [x] 1.2 Add GZipMiddleware to the middleware stack
    - Insert `django.middleware.gzip.GZipMiddleware` after SecurityMiddleware and before WhiteNoiseMiddleware in `MIDDLEWARE` list
    - Final order: SecurityMiddleware → GZipMiddleware → WhiteNoiseMiddleware → SessionMiddleware → ...
    - _Requirements: 10.1, 10.2, 14.1, 14.2_

  - [x] 1.3 Verify database connection persistence configuration
    - Confirm `conn_max_age=600` and `conn_health_checks=True` are set in `dj_database_url.parse()` call
    - Add a comment documenting the connection limit strategy (1 connection per gunicorn worker, max 5 total)
    - _Requirements: 7.1, 7.2, 7.5, 15.1, 15.8_

- [x] 2. Database index strategy
  - [x] 2.1 Add composite index on User model for officer queries
    - Add `models.Index(fields=['organization', 'is_active', 'role'])` to `accounts/models.py` User Meta.indexes
    - Generate migration via `python manage.py makemigrations accounts`
    - _Requirements: 4.5, 4.7_

  - [x] 2.2 Verify existing indexes on Task, TaskAssignment, and Notification models
    - Confirm Task model has indexes for (organization, is_archived, status), (organization, due_date), (status, due_date), (-created_at)
    - Confirm TaskAssignment has (officer, task) and (task) indexes
    - Confirm Notification has (recipient, is_read, -created_at) and (recipient, -created_at) indexes
    - Fix Task index field order if needed: requirements specify (organization, is_archived, status) but existing code has (organization, status, is_archived)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.7_

- [x] 3. Checkpoint - Ensure migrations run cleanly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Query optimization for Dashboard and Charts API
  - [x] 4.1 Optimize DashboardStatsAPIView with conditional aggregation
    - Replace four separate `.count()` queries with a single `aggregate()` using conditional `Count` expressions for active, completed, overdue, and upcoming counts
    - Active statuses: not_started, processing, to_advisers, accounting, oca, osas, ppss, supply
    - Ensure no more than 2 database queries per request
    - _Requirements: 1.1, 3.1, 1.6_

  - [x] 4.2 Optimize DashboardChartsAPIView status and priority distributions
    - Replace per-status and per-priority loop queries with a single `aggregate()` using conditional `Count` for all 9 statuses and all 4 priorities
    - _Requirements: 1.3_

  - [x] 4.3 Optimize DashboardChartsAPIView monthly completions with TruncMonth
    - Replace per-month loop queries with a single `TruncMonth` annotated query counting completed tasks by month
    - _Requirements: 1.4_

  - [x] 4.4 Optimize DashboardChartsAPIView tasks per officer query
    - Ensure single annotated queryset with `Count` grouping, ordered by count descending, limited to top 8 officers using database-level `[:8]` slicing
    - _Requirements: 1.5, 11.3_

  - [x] 4.5 Optimize DashboardChartsAPIView weekly trend
    - Replace per-day loop queries with a single annotated query using `TruncDate` or equivalent batch approach
    - _Requirements: 1.6_

  - [ ]* 4.6 Write property test for conditional aggregation equivalence
    - **Property 1: Conditional Aggregation Equivalence**
    - Use Hypothesis to generate tasks with arbitrary statuses and verify single aggregate() produces same counts as separate filtered count() queries
    - **Validates: Requirements 1.1, 1.3, 3.1, 12.1**

  - [ ]* 4.7 Write property test for TruncMonth aggregation correctness
    - **Property 2: TruncMonth Aggregation Correctness**
    - Use Hypothesis to generate completed tasks across multiple months and verify TruncMonth annotation counts match per-month filtered counts
    - **Validates: Requirements 1.4**

  - [ ]* 4.8 Write property test for top-N aggregation correctness
    - **Property 12: Top-N Aggregation Correctness**
    - Use Hypothesis to generate task assignments across >8 officers and verify top-8 query returns correct officers in correct order
    - **Validates: Requirements 1.5, 11.3**

- [x] 5. Kanban board single-query architecture
  - [x] 5.1 Refactor TaskBoardView to use single-fetch partitioning
    - Fetch all non-archived tasks matching filters in one queryset with `select_related` and `prefetch_related`
    - Partition into status groups using Python iteration instead of per-column DB queries
    - Apply `[:50]` limit per column during Python partitioning (ordered by `-created_at`)
    - Include empty columns for statuses with zero tasks
    - Ensure no more than 4 total database queries (1 main + up to 3 prefetch)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 11.2_

  - [x] 5.2 Cache officers list for Kanban board filter dropdowns
    - Use cache key `org_{org_id}_officers` with TTL of 60 seconds for the officers dropdown
    - Apply same caching pattern already used in TaskListView
    - _Requirements: 5.1_

  - [ ]* 5.3 Write property test for status partitioning
    - **Property 3: Status Partitioning with Limit and Ordering**
    - Use Hypothesis to generate tasks with arbitrary statuses/timestamps and verify: correct membership, correct counts, max 50 per group, descending order, all non-completed statuses present
    - **Validates: Requirements 2.2, 2.3, 2.4, 2.5, 11.2**

- [x] 6. N+1 query elimination in API endpoints
  - [x] 6.1 Optimize TaskListAPIView with select_related and values()
    - Add `select_related('created_by', 'organization')` and use `.values()` with only the required fields (id, task_number, title, status, priority, progress, due_date)
    - Apply `[:50]` limit at database level
    - _Requirements: 3.2, 8.1, 8.2, 11.5_

  - [x] 6.2 Optimize UnreadNotificationsAPIView with select_related and only()
    - Add `select_related('related_task')` and `.only('id', 'title', 'message', 'notification_type', 'created_at')` to notification queryset
    - Limit to 10 notifications
    - Return only fields: id, title, message, type, created_at
    - _Requirements: 3.3, 8.4_

  - [x] 6.3 Optimize TaskCalendarEventsView with prefetch_related
    - Ensure `prefetch_related('assigned_officers', 'assigned_officers__officer_profile', 'assigned_officers__officer_profile__position')` is applied before iteration
    - Verify query count does not increase with number of tasks
    - _Requirements: 3.4_

  - [ ]* 6.4 Write property test for N+1 elimination invariant
    - **Property 4: N+1 Query Elimination Invariant**
    - Use Django TestCase with `assertNumQueries` to verify query count with 1 result object equals query count with 50 result objects for optimized endpoints
    - **Validates: Requirements 3.6**

- [x] 7. Checkpoint - Verify query optimization
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Caching strategy implementation
  - [x] 8.1 Standardize officer list caching with correct cache key format
    - Update TaskListView and TaskBoardView to use cache key `org_{org_id}_officers` (standardized format)
    - TTL of 60 seconds
    - _Requirements: 5.1_

  - [x] 8.2 Implement dashboard charts caching
    - Cache DashboardChartsAPIView response using key `dashboard_charts_{user_id}_{org_id}_{scope}` with TTL of 30 seconds
    - Fall back to fresh query on cache miss without raising errors
    - _Requirements: 5.5, 5.6_

  - [x] 8.3 Implement cache invalidation on task mutations
    - Create `invalidate_task_caches(task)` utility function in tasks app
    - Invalidate `org_{org_id}_officers` and `notif_unread_{user_id}` for all assigned officers on task create/update/delete/status change
    - Invalidate dashboard chart cache keys for the task creator
    - Call from TaskCreateView, TaskUpdateView, TaskDeleteView, TaskMoveStatusView, TaskBulkCompleteView
    - _Requirements: 5.4_

  - [x] 8.4 Implement reports officer list caching
    - Cache officers list in ReportsDashboardView using key `reports_officers_{org_id}` with TTL of 300 seconds
    - _Requirements: 12.3, 15.6_

  - [ ]* 8.5 Write property test for cache round-trip correctness
    - **Property 5: Cache Round-Trip Correctness**
    - Use Hypothesis to generate cacheable values, store in cache, and verify retrieval within TTL returns identical value
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.5, 12.3**

  - [ ]* 8.6 Write property test for cache invalidation on mutation
    - **Property 6: Cache Invalidation on Mutation**
    - Generate task mutations and verify cache keys are deleted after mutation
    - **Validates: Requirements 5.4**

  - [ ]* 8.7 Write property test for cache miss graceful fallback
    - **Property 7: Cache Miss Graceful Fallback**
    - Verify that when cache returns None, fresh DB query executes without exception
    - **Validates: Requirements 5.6**

- [x] 9. API response optimization
  - [x] 9.1 Add Cache-Control headers to API endpoints
    - Add `Cache-Control: private, max-age=0` to TaskListAPIView and UnreadNotificationsAPIView responses
    - Add `Cache-Control: private, max-age=30` to DashboardStatsAPIView and DashboardChartsAPIView responses
    - _Requirements: 8.5_

  - [x] 9.2 Ensure DashboardChartsAPIView returns chart-ready data structure
    - Verify each chart dataset has a "labels" array and "data" array of equal length
    - No client-side grouping/counting/reshaping required
    - _Requirements: 8.3_

  - [ ]* 9.3 Write property test for API response field limiting
    - **Property 8: API Response Field Limiting**
    - Verify TaskListAPIView returns exactly {id, task_number, title, status, priority, progress, due_date} per task
    - Verify UnreadNotificationsAPIView returns exactly {id, title, message, type, created_at} per notification
    - **Validates: Requirements 8.1, 8.4**

  - [ ]* 9.4 Write property test for API response list bounding
    - **Property 9: API Response List Bounding**
    - Use Hypothesis to generate varying numbers of records and verify TaskListAPIView returns ≤50 and UnreadNotificationsAPIView returns ≤10
    - **Validates: Requirements 8.2, 8.4**

  - [ ]* 9.5 Write property test for chart data structural invariant
    - **Property 10: Chart Data Structural Invariant**
    - Verify every dataset in DashboardChartsAPIView response has labels and data arrays of equal length
    - **Validates: Requirements 8.3**

- [x] 10. Reports view query optimization
  - [x] 10.1 Consolidate ReportsDashboardView summary statistics into single query
    - Replace separate count() calls for total, completed, overdue, and in_progress with a single `aggregate()` using conditional `Count` expressions
    - Ensure no more than 3 database queries for the entire page (tasks, officers dropdown, aggregate counts)
    - _Requirements: 12.1, 12.2, 12.6_

  - [x] 10.2 Implement export batching for large querysets
    - Modify ExportReportPDFView and ExportReportExcelView to use `iterator(chunk_size=200)` when queryset exceeds 500 tasks
    - Process in batches of 200 to limit peak memory consumption
    - _Requirements: 12.4, 12.5_

  - [ ]* 10.3 Write property test for export batching equivalence
    - **Property 13: Export Batching Equivalence**
    - Use Hypothesis to generate large querysets and verify iterator(chunk_size=200) yields all tasks in same order with no duplicates or omissions
    - **Validates: Requirements 12.4, 12.5**

- [x] 11. Permission check optimization
  - [x] 11.1 Optimize can_edit_task and can_update_task_progress with prefetch-aware checks
    - Modify `can_edit_task` and `can_update_task_progress` in `accounts/models.py` to check `_prefetched_objects_cache` before issuing filter().exists() query
    - If prefetch cache has 'assigned_officers', use Python iteration instead of DB query
    - _Requirements: 13.1_

  - [x] 11.2 Ensure request-level organization caching in permission checks
    - Verify `get_organization()` caches result on `request._cached_org` for subsequent calls
    - Ensure TenantScopedQuerySetMixin accesses user.organization without extra SELECT
    - _Requirements: 13.2, 13.3, 13.5_

  - [x] 11.3 Limit check_org_admin_password queryset
    - Add `.order_by('-date_joined')[:10]` limit to the admin users queryset in `check_org_admin_password` function in `tasks/views.py`
    - Prevent unbounded iteration in orgs with many admins
    - _Requirements: 13.4_

  - [ ]* 11.4 Write property test for prefetch-aware permission check
    - **Property 14: Prefetch-Aware Permission Check**
    - Verify can_edit_task returns same boolean with prefetch cache as with fresh filter().exists() query, without additional DB query when prefetch is populated
    - **Validates: Requirements 13.1**

  - [ ]* 11.5 Write property test for request-level organization caching
    - **Property 15: Request-Level Organization Caching**
    - Verify multiple calls to get_organization() within same request return same instance without extra queries
    - **Validates: Requirements 13.2, 13.5**

- [x] 12. Template rendering optimization
  - [x] 12.1 Ensure zero-query template rendering for task list rows
    - Verify TaskListView template only accesses pre-fetched relationships
    - Remove any template-level `.filter()` or `.exists()` calls on related managers
    - Use pre-computed annotations or prefetch caches for all data displayed in task rows
    - _Requirements: 9.1, 9.4, 9.5_

  - [x] 12.2 Ensure Kanban board template uses pre-partitioned lists
    - Verify the board template iterates `columns[].tasks` list directly (max 50 per column)
    - No template-level queryset filtering
    - _Requirements: 9.3_

  - [x] 12.3 Ensure context processors return cached values with zero queries on cache hit
    - Verify notifications_processor returns cached unread count (TTL 30s) without DB query
    - Verify organization_processor returns cached approved orgs list (TTL 60s) without DB query
    - _Requirements: 9.2, 5.2, 5.3_

  - [ ]* 12.4 Write property test for context processor zero-query on cache hit
    - **Property 16: Context Processor Zero-Query on Cache Hit**
    - Use Django TestCase with assertNumQueries(0) to verify context processors execute no queries when cache is populated
    - **Validates: Requirements 9.2**

- [x] 13. Checkpoint - Verify all optimizations
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Middleware and response verification
  - [x] 14.1 Verify middleware stack order and static file short-circuit
    - Write test confirming MIDDLEWARE list order: SecurityMiddleware, GZipMiddleware, WhiteNoiseMiddleware, SessionMiddleware, ...
    - Confirm WhiteNoise handles static requests without invoking downstream middleware
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 14.2 Verify GZip compression behavior
    - Confirm responses >200 bytes with text/html or application/json Content-Type are compressed when client sends Accept-Encoding: gzip
    - Confirm PDF/Excel download responses are NOT compressed
    - Confirm responses <200 bytes are not compressed
    - _Requirements: 14.1, 14.3, 14.4, 14.5, 14.6_

  - [ ]* 14.3 Write unit tests for middleware configuration
    - Test middleware ordering positions
    - Test GZip compression applies correctly
    - Test static file Cache-Control headers
    - _Requirements: 10.1, 10.2, 14.1, 14.2, 6.2_

- [x] 15. Pagination and queryset bounding verification
  - [x] 15.1 Verify TaskListView uses database-level LIMIT/OFFSET
    - Confirm paginate_by=10 causes Django to generate SQL with LIMIT and OFFSET
    - Ensure ordering is applied before pagination
    - _Requirements: 11.1_

  - [x] 15.2 Verify no unbounded querysets exist in views or API endpoints
    - Audit all views and API endpoints to confirm explicit upper bounds (pagination or [:N] slicing) on all evaluated querysets
    - _Requirements: 11.4, 11.5_

  - [ ]* 15.3 Write property test for pagination bounded results
    - **Property 11: Pagination Produces Bounded Results**
    - Verify evaluated queryset for any page contains at most page_size records
    - **Validates: Requirements 11.1**

- [x] 16. Final checkpoint - Ensure all tests pass
=======
This implementation plan optimizes the CSG Task Management System across database queries, caching, static assets, deployment configuration, frontend rendering, and observability. Each task builds incrementally, starting with infrastructure (settings, middleware, utilities) and progressing through view-level optimizations, bulk operations, and finally integration wiring. Python with Django ORM is used throughout.

## Tasks

- [x] 1. Set up infrastructure and utility modules
  - [x] 1.1 Create query utility module with aggregate helper functions
    - Create `core/query_utils.py` with `group_tasks_by_status`, `get_distributions`, `get_monthly_completed`, `get_weekly_trend`, `get_dashboard_stats`, and `get_report_counts` functions
    - Each function uses Django ORM aggregation (conditional Count, TruncMonth, TruncDate) instead of per-item loops
    - _Requirements: 2.1, 2.3, 2.4, 2.5, 2.6, 2.7, 9.1, 9.4_

  - [x] 1.2 Create cache utility module with safe cache helpers and invalidation functions
    - Create `core/cache_utils.py` with `safe_cache_get`, `invalidate_task_caches`, `get_dashboard_cache_key`, `invalidate_officers_cache`, and `invalidate_org_cache` functions
    - `safe_cache_get` must catch all exceptions on read/write and fall back to database query
    - Cache key format follows `{resource}_{scope}_{identifier}` pattern
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 13.4_

  - [x] 1.3 Create performance monitoring middleware
    - Create `PerformanceMonitoringMiddleware` in `core/middleware.py`
    - Track query count and request duration per request
    - Add `X-Query-Count` and `X-Query-Time-Ms` headers only when `DEBUG=True`
    - Log WARNING to `csg.performance` logger when query count exceeds `PERF_QUERY_COUNT_THRESHOLD` (default 15) or duration exceeds `PERF_REQUEST_DURATION_THRESHOLD_MS` (default 2000ms)
    - _Requirements: 12.2, 12.3, 12.4, 12.6_

  - [x] 1.4 Create database retry middleware
    - Create `DatabaseRetryMiddleware` in `core/middleware.py`
    - Catch `OperationalError` on connection failures, close connection, retry once
    - Return HTTP 503 with friendly message if retry also fails
    - _Requirements: 8.4_

  - [x]* 1.5 Write unit tests for query utility functions
    - Test `get_distributions`, `get_dashboard_stats`, `get_report_counts`, `group_tasks_by_status` with empty querysets, single items, and multiple statuses/priorities
    - Test `get_monthly_completed` and `get_weekly_trend` with various date ranges
    - _Requirements: 2.1, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

  - [x]* 1.6 Write unit tests for cache utility functions
    - Test `safe_cache_get` with cache hit, cache miss, cache error, and corrupt data
    - Test `invalidate_task_caches` deletes correct keys
    - Test `get_dashboard_cache_key` format includes user_id, scope, org_id, version
    - _Requirements: 7.5, 7.6, 7.7_

- [x] 2. Configure deployment and static asset settings
  - [x] 2.1 Configure Gunicorn production settings
    - Create `gunicorn.conf.py` at project root with: `worker_class='gthread'`, `workers=4` (via WEB_CONCURRENCY), `threads=2`, `timeout=120`, `keepalive=5`, `max_requests=1000`, `max_requests_jitter=50`
    - Bind to `0.0.0.0:{PORT}` with accesslog/errorlog to stdout
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

  - [x] 2.2 Configure WhiteNoise and static file storage in settings
    - Set `WHITENOISE_MAX_AGE = 31536000` and `WHITENOISE_ALLOW_ALL_ORIGINS = True`
    - Use `CompressedManifestStaticFilesStorage` when `DEBUG=False`, `StaticFilesStorage` when `DEBUG=True`
    - Add `brotli` to `requirements.txt` with pinned version for WhiteNoise Brotli pre-compression
    - Update `build.sh` to run collectstatic which produces .gz and .br variants
    - _Requirements: 5.1, 5.2, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 2.3 Configure database connection settings for Neon PostgreSQL
    - Set `CONN_MAX_AGE=600`, `CONN_HEALTH_CHECKS=True`
    - Add OPTIONS: `connect_timeout=10`, `keepalives_idle=30`
    - Enforce SSL when DATABASE_URL is not localhost/127.0.0.1
    - _Requirements: 8.1, 8.2, 8.3, 8.5, 8.6_

  - [x] 2.4 Configure Django Debug Toolbar and performance logging settings
    - Add Django Debug Toolbar to INSTALLED_APPS and middleware only when `DEBUG=True`
    - Add `PERF_QUERY_COUNT_THRESHOLD` and `PERF_REQUEST_DURATION_THRESHOLD_MS` settings
    - Configure `csg.performance` logger
    - Enable database query logging at WARNING level for queries >100ms when DEBUG=True
    - _Requirements: 12.1, 12.2, 12.3, 12.5, 12.6_

  - [x] 2.5 Update base template for CDN and asset loading optimization
    - Load Bootstrap CSS (5.3.2) and Bootstrap Icons CSS (1.11.3) from cdn.jsdelivr.net with version-pinned URLs
    - Add `defer` attribute to table-sort.js script tag
    - Inline critical CSS for `#nav-progress` and `.chart-loading-overlay` in a `<style>` element in the head
    - _Requirements: 5.3, 5.4, 5.5_

- [x] 3. Checkpoint - Ensure infrastructure builds correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Optimize context processors
  - [x] 4.1 Optimize notification context processor with caching
    - Return immediately with empty defaults for unauthenticated users (zero queries)
    - Check cache for `notif_unread_{user_id}` key; if warm, return cached value (zero queries)
    - On cold cache: execute COUNT query for unread + SELECT for 5 recent notifications using `only()` on id, title, notification_type, is_read, created_at, related task id and task_number
    - Cache unread count with 30-second TTL
    - _Requirements: 3.1, 3.2, 3.5, 3.6_

  - [x] 4.2 Optimize organization context processor with caching
    - Return immediately with empty defaults for unauthenticated users (zero queries)
    - For non-super-admin users: return organization from already-loaded User FK (zero additional queries)
    - For super-admin users: cache approved organizations list (id, name, abbreviation only) with 60-second TTL using single shared cache key `approved_orgs_list`
    - _Requirements: 3.3, 3.4, 3.6_

  - [x]* 4.3 Write unit tests for context processor optimizations
    - Test notification processor with warm cache, cold cache, and unauthenticated user
    - Test organization processor with super admin, org admin, and unauthenticated user
    - Assert query counts using `assertNumQueries`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_

- [x] 5. Optimize task views
  - [x] 5.1 Optimize TaskListView queryset with select_related and prefetch_related
    - Ensure no more than 4 queries for the view's own logic (base queryset, pagination count, officers list cache check, paginated result fetch)
    - Use prefetched related data for officer display names and positions in template
    - Maintain pagination at 10 items per page
    - _Requirements: 1.1, 1.6, 10.4, 11.1_

  - [x] 5.2 Optimize TaskBoardView with single base queryset and aggregated counts
    - Replace per-column querysets with single base queryset using `select_related`/`prefetch_related`, then group in Python via `group_tasks_by_status`
    - Replace per-column count queries with single aggregate Count query grouped by status
    - Cap per-column display at 50 tasks with overflow indicator showing total count
    - _Requirements: 1.2, 1.3, 1.6, 10.6_

  - [x] 5.3 Optimize TaskCalendarEventsView with prefetch for assigned officers
    - Prefetch assigned officer data (officer_profile and position) so iteration triggers zero additional queries
    - _Requirements: 1.4_

  - [x] 5.4 Optimize TaskDetailView with comprehensive prefetch
    - Prefetch comments (with author), attachments, history (with changed_by), and assigned officers (with officer_profile and position)
    - Ensure no more than 6 total queries for the detail page excluding context processor queries
    - _Requirements: 1.5_

  - [x]* 5.5 Write integration tests for task view query counts
    - Test TaskListView query count ≤4 with warm and cold cache
    - Test TaskBoardView single base query + single aggregate count
    - Test TaskDetailView ≤6 queries
    - Test TaskCalendarEventsView zero N+1 on assigned officers
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 6. Optimize dashboard, monitoring, and report views
  - [x] 6.1 Optimize DashboardView with single aggregate query for task counts
    - Replace four separate count queries with `get_dashboard_stats` single aggregate
    - Cache dashboard counts per user and scope with 30-second TTL
    - _Requirements: 2.1, 7.2_

  - [x] 6.2 Optimize MonitoringView with annotated queryset for officer metrics
    - Replace per-officer method calls with single annotated queryset for all officer metrics (total, completed, active, overdue tasks)
    - Limit to 50 officers sorted by completion rate descending
    - _Requirements: 2.2, 10.5_

  - [x] 6.3 Optimize ReportsDashboardView with single aggregate and pagination
    - Replace multiple `count()` calls with `get_report_counts` single aggregate
    - Paginate filtered task list at 25 items per page instead of loading all into context
    - _Requirements: 2.5, 11.3_

  - [x] 6.4 Write integration tests for dashboard and monitoring view optimizations
    - Test DashboardView single aggregate query with `assertNumQueries(1)` for counts
    - Test MonitoringView single annotated queryset regardless of officer count
    - Test ReportsDashboardView single aggregate for counts and pagination at 25 items
    - _Requirements: 2.1, 2.2, 2.5_

- [x] 7. Optimize API endpoints
  - [x] 7.1 Optimize DashboardChartsAPIView with conditional Count aggregates
    - Compute status + priority distributions in a single aggregate query using conditional Count
    - Use `get_monthly_completed` (TruncMonth) for monthly data in one query
    - Use `get_weekly_trend` (TruncDate) for weekly trend data in one query
    - Set `Cache-Control: max-age=15` response header
    - _Requirements: 2.3, 2.4, 2.6, 2.7, 9.1, 9.5_

  - [x] 7.2 Optimize TaskListAPIView and UnreadNotificationsAPIView
    - TaskListAPIView: use `select_related('organization')` and `only()` limited to id, task_number, title, status, priority, progress, due_date
    - UnreadNotificationsAPIView: use `select_related('related_task')` and `only()` limited to id, title, message, notification_type, created_at, related_task_id
    - _Requirements: 9.2, 9.3_

  - [x] 7.3 Optimize DashboardStatsAPIView with single aggregate
    - Replace 4 separate count() calls with `get_dashboard_stats` single conditional Count aggregate
    - _Requirements: 9.4_

  - [x]* 7.4 Write integration tests for API endpoint query counts
    - Test DashboardChartsAPIView ≤1 query for distributions, ≤1 for monthly, ≤1 for weekly
    - Test DashboardStatsAPIView exactly 1 query for all counts
    - Test TaskListAPIView and UnreadNotificationsAPIView field limiting
    - Assert all responses return within reasonable time
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [x] 8. Checkpoint - Ensure all view optimizations work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement bulk operation optimizations
  - [x] 9.1 Create bulk operations service with transactional bulk_update/bulk_create
    - Create `bulk_complete_tasks` in `tasks/services.py` using `bulk_update` for task fields + `bulk_create` for TaskHistory + `bulk_create` for Notifications, all within `transaction.atomic()`
    - Create `bulk_reassign_officers` using single delete + `bulk_create` within `transaction.atomic()`
    - Cap bulk operations at 50 tasks per request
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7_

  - [x] 9.2 Integrate bulk service into TaskBulkCompleteView and TaskUpdateView
    - Replace per-task save() loops in TaskBulkCompleteView with `bulk_complete_tasks` service call
    - Replace per-officer assignment creation in TaskUpdateView with `bulk_reassign_officers` service call
    - Ensure error handling rolls back transaction and returns error message
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

  - [x]* 9.3 Write integration tests for bulk operations
    - Test bulk complete with 1, 10, and 50 tasks asserting ≤3 write queries
    - Test bulk reassign with empty list, single officer, and multiple officers
    - Test transaction rollback on simulated failure
    - _Requirements: 14.5, 14.6, 14.7_

- [x] 10. Implement caching strategy with invalidation hooks
  - [x] 10.1 Add cache reads to officers list views and dashboard views
    - Cache officers list per organization with 60-second TTL in officers list view
    - Use `get_dashboard_cache_key` for versioned dashboard count caching with 30-second TTL
    - Include organization identifier in all organization-scoped cache keys
    - _Requirements: 7.1, 7.2, 7.5, 7.6_

  - [x] 10.2 Add cache invalidation on Task and Officer model mutations
    - On Task create/update/delete: call `invalidate_task_caches(organization_id)` to bump dashboard version and clear officers list cache
    - On Officer create/update/delete: call `invalidate_officers_cache(organization_id)`
    - On Organization status change: call `invalidate_org_cache()`
    - Invalidation must happen within the same request-response cycle
    - _Requirements: 7.1, 7.3, 7.4, 13.6_

  - [x]* 10.3 Write integration tests for caching and invalidation
    - Test cache hit returns data without DB queries
    - Test cache miss queries DB and populates cache
    - Test mutation invalidates correct cache keys
    - Test tenant isolation: user in org A cannot access org B cached data
    - _Requirements: 7.1, 7.4, 7.6, 7.7, 13.4_

- [x] 11. Optimize pagination and fragment rendering
  - [x] 11.1 Ensure consistent pagination across all list views
    - TaskListView: 10 items per page
    - NotificationListView: 20 items per page
    - ReportsDashboardView: 25 items per page
    - ActivityLog: 50 items per page, ordered by timestamp descending
    - Use COUNT query for total items (not loading all objects into memory)
    - Return last available page if requested page exceeds total
    - Preserve all active filter and sort parameters in pagination links
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

  - [x] 11.2 Verify and optimize FragmentResponseMixin
    - Ensure fragment responses contain only content between FRAGMENT_START/FRAGMENT_END markers plus FRAGMENT_SCRIPTS content
    - Set Content-Length header on fragment responses
    - Graceful degradation: return full page with X-Fragment-Response and X-Page-Title headers if markers not found
    - _Requirements: 10.1, 10.2, 10.3_

  - [x]* 11.3 Write integration tests for pagination and fragment rendering
    - Test each view's pagination limit is enforced
    - Test out-of-bounds page number returns last page
    - Test filter/sort params preserved in pagination links
    - Test fragment response extracts only marked content
    - Test graceful degradation when markers are missing
    - _Requirements: 10.1, 10.2, 10.3, 11.1, 11.2, 11.6, 11.7_

- [x] 12. Verify database indexes and regression prevention
  - [x] 12.1 Verify all required composite indexes exist in model Meta
    - Confirm Task index on `(organization_id, is_archived, status)` exists
    - Confirm TaskAssignment index on `(officer_id, task_id)` exists
    - Confirm Notification index on `(recipient_id, is_read, -created_at)` exists
    - Confirm ActivityLog index on `(organization_id, -timestamp)` exists
    - Add code comments on existing indexes stating which query patterns they cover
    - Do not add redundant indexes; verify total per model ≤6
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [x] 12.2 Add regression prevention verification to existing views
    - Ensure all URL patterns and view behaviors remain unchanged
    - Verify tenant isolation via TenantScopedQuerySetMixin returns same result sets
    - Verify role-based access controls produce same allow/deny decisions
    - Ensure cached data respects tenant boundaries
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

  - [x]* 12.3 Write property test for query optimization equivalence
    - **Property 1: Query Optimization Equivalence**
    - Verify optimized aggregate functions produce identical output to naive loop-based count() calls for random task sets with varying statuses, priorities, and dates
    - **Validates: Requirements 2.8**

  - [x]* 12.4 Write property test for cache-database equivalence
    - **Property 2: Cache-Database Equivalence**
    - Verify cached response content is semantically equivalent to fresh DB query response for random user/org/filter combinations
    - **Validates: Requirements 13.5**

  - [x]* 12.5 Write property test for cache tenant isolation
    - **Property 3: Cache Tenant Isolation**
    - Verify cache keys for two users in different organizations have zero intersection for organization-scoped data
    - **Validates: Requirements 7.6, 13.4**

  - [x]* 12.6 Write property test for view-level tenant isolation preservation
    - **Property 4: View-Level Tenant Isolation Preservation**
    - Verify optimized views return same task records as original views for same user/org context across random multi-tenant datasets
    - **Validates: Requirements 13.2**

  - [x]* 12.7 Write property test for fragment extraction correctness
    - **Property 5: Fragment Extraction Correctness**
    - Verify FragmentResponseMixin returns exactly marker-bounded content and excludes sidebar/topbar/modal HTML for random HTML with markers at various positions
    - **Validates: Requirements 10.1**

  - [x]* 12.8 Write property test for pagination filter preservation
    - **Property 6: Pagination Filter Preservation**
    - Verify all filter and sort parameters are preserved in pagination links for random parameter dictionaries
    - **Validates: Requirements 11.7**

  - [x]* 12.9 Write property test for bulk operation bounded queries
    - **Property 7: Bulk Operation Bounded Queries**
    - Verify bulk complete executes at most 3 write queries for any task count N where 1 ≤ N ≤ 50
    - **Validates: Requirements 14.7**

  - [x]* 12.10 Write property test for cache invalidation on mutation
    - **Property 8: Cache Invalidation on Mutation**
    - Verify task create/update/delete invalidates correct organization cache keys within same request-response cycle
    - **Validates: Requirements 7.4, 13.6**

- [x] 13. Final checkpoint - Ensure all tests pass
>>>>>>> fix/optimization
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
<<<<<<< HEAD
- Property tests use Hypothesis (Python PBT library) and validate universal correctness properties from the design
- Unit tests validate specific examples and edge cases
- The design uses Python/Django — all implementation is in Python
- Existing optimizations (Dashboard conditional aggregation, notification caching, officer list caching) should be verified and standardized rather than rewritten
- All changes must stay within Neon free-tier (≤5 connections), Render free-tier (1-2 workers), and file-based cache (no Redis/Memcached)
=======
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases
- The design confirmed all required database indexes already exist — task 12.1 is verification + documentation only
- File-based cache is used (no Redis) per Render free-tier constraint
- All optimizations preserve existing URL patterns, tenant isolation, and role-based access
>>>>>>> fix/optimization

## Task Dependency Graph

```json
{
  "waves": [
<<<<<<< HEAD
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "2.2"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5", "5.1", "6.1", "6.2", "6.3"] },
    { "id": 3, "tasks": ["4.6", "4.7", "4.8", "5.2", "5.3", "6.4", "8.1"] },
    { "id": 4, "tasks": ["8.2", "8.3", "8.4", "9.1", "9.2", "10.1", "11.1", "11.2", "11.3"] },
    { "id": 5, "tasks": ["8.5", "8.6", "8.7", "9.3", "9.4", "9.5", "10.2", "10.3", "11.4", "11.5"] },
    { "id": 6, "tasks": ["12.1", "12.2", "12.3", "14.1", "14.2", "15.1", "15.2"] },
    { "id": 7, "tasks": ["12.4", "14.3", "15.3"] }
=======
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "2.1", "2.3"] },
    { "id": 1, "tasks": ["1.5", "1.6", "2.2", "2.4", "2.5"] },
    { "id": 2, "tasks": ["4.1", "4.2", "5.1", "5.3", "5.4"] },
    { "id": 3, "tasks": ["4.3", "5.2", "6.1", "6.2", "6.3"] },
    { "id": 4, "tasks": ["5.5", "6.4", "7.1", "7.2", "7.3"] },
    { "id": 5, "tasks": ["7.4", "9.1"] },
    { "id": 6, "tasks": ["9.2", "9.3", "10.1"] },
    { "id": 7, "tasks": ["10.2", "10.3", "11.1", "11.2"] },
    { "id": 8, "tasks": ["11.3", "12.1", "12.2"] },
    { "id": 9, "tasks": ["12.3", "12.4", "12.5", "12.6", "12.7", "12.8", "12.9", "12.10"] }
>>>>>>> fix/optimization
  ]
}
```

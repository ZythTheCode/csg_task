# Implementation Plan: Performance Optimization

## Overview

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
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases
- The design confirmed all required database indexes already exist — task 12.1 is verification + documentation only
- File-based cache is used (no Redis) per Render free-tier constraint
- All optimizations preserve existing URL patterns, tenant isolation, and role-based access

## Task Dependency Graph

```json
{
  "waves": [
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
  ]
}
```

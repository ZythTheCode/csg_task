# Implementation Plan: Performance Optimization

## Overview

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
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests use Hypothesis (Python PBT library) and validate universal correctness properties from the design
- Unit tests validate specific examples and edge cases
- The design uses Python/Django — all implementation is in Python
- Existing optimizations (Dashboard conditional aggregation, notification caching, officer list caching) should be verified and standardized rather than rewritten
- All changes must stay within Neon free-tier (≤5 connections), Render free-tier (1-2 workers), and file-based cache (no Redis/Memcached)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "2.2"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5", "5.1", "6.1", "6.2", "6.3"] },
    { "id": 3, "tasks": ["4.6", "4.7", "4.8", "5.2", "5.3", "6.4", "8.1"] },
    { "id": 4, "tasks": ["8.2", "8.3", "8.4", "9.1", "9.2", "10.1", "11.1", "11.2", "11.3"] },
    { "id": 5, "tasks": ["8.5", "8.6", "8.7", "9.3", "9.4", "9.5", "10.2", "10.3", "11.4", "11.5"] },
    { "id": 6, "tasks": ["12.1", "12.2", "12.3", "14.1", "14.2", "15.1", "15.2"] },
    { "id": 7, "tasks": ["12.4", "14.3", "15.3"] }
  ]
}
```

# Implementation Plan: UI Performance Optimization

## Overview

Transform the CSG Task Management System from a full-page-reload application to one that performs AJAX-based partial page updates with skeleton loading states and intelligent prefetching. Uses vanilla JavaScript, a Django FragmentResponseMixin, LRU content cache, and hover-based prefetching — all within free-tier hosting constraints.

## Tasks

- [x] 1. Create FragmentResponseMixin (Server-Side Foundation)
  - [x] 1.1 Create `core/mixins.py` with `FragmentResponseMixin` class that detects `X-Requested-With: XMLHttpRequest` and `X-Fragment: true` request headers
    - Implement `_is_fragment_request()` method and `render_to_response` override
    - _Requirements: 2.1, 2.4_
  - [x] 1.2 Add fragment markers (`<!-- FRAGMENT_START -->`, `<!-- FRAGMENT_END -->`, `<!-- FRAGMENT_SCRIPTS_START -->`, `<!-- FRAGMENT_SCRIPTS_END -->`) to `templates/base.html` around the content block and extra_js block
    - _Requirements: 2.1, 2.5_
  - [x] 1.3 Implement the `render_to_response` override that extracts HTML between fragment markers and returns only the content + scripts with `X-Page-Title` and `X-Fragment-Response` headers
    - _Requirements: 2.1, 2.3, 2.5_
  - [x] 1.4 Add the mixin to `DashboardView` in `core/views.py` and verify it returns full HTML for standard requests and fragment-only HTML for fragment requests
    - _Requirements: 2.2, 2.4_
  - [x] 1.5 Add the mixin to all primary views: `TaskListView`, `TaskBoardView`, `TaskCalendarView`, `OfficerListView`, `NotificationListView`, `ReportsDashboardView`
    - _Requirements: 2.4_
  - [ ]* 1.6 Write a Django test that verifies fragment responses contain only content (no `<html>`, `<head>`, sidebar markup) and include the `X-Page-Title` header
    - **Property 1: Fragment Subset**
    - **Property 6: No Additional Database Queries**
    - **Validates: Requirements 2.1, 2.2, 2.5, 10.3**

- [x] 2. Create Skeleton Loading CSS and Templates
  - [x] 2.1 Create `static/css/skeleton.css` with base skeleton styles: `.skeleton-line`, `.skeleton-circle`, `.skeleton-card` classes with shimmer animation keyframes, dark mode support via `[data-mode="dark"]` selector, and width utility classes
    - _Requirements: 5.4, 5.5, 10.2_
  - [x] 2.2 Create skeleton template partials in `templates/skeletons/`: `_task_list.html` (8 rows with task number, title, badges), `_kanban.html` (4 columns with cards), `_dashboard.html` (4 stat cards + recent tasks list)
    - _Requirements: 5.1, 5.2_
  - [x] 2.3 Create skeleton template partials: `_calendar.html` (month grid), `_officers.html` (officer cards), `_notifications.html` (notification items)
    - _Requirements: 5.2_
  - [x] 2.4 Add `<template>` elements to `base.html` that include each skeleton partial, with `id` attributes matching page types (e.g., `skeleton-tasks-list`, `skeleton-tasks-board`)
    - _Requirements: 5.1, 5.2_
  - [x] 2.5 Ensure all skeleton elements have `aria-hidden="true"` and verify total CSS file size stays under 5KB
    - _Requirements: 11.4, 10.2_

- [x] 3. Create Top Progress Bar (Cold-Start Friendly)
  - [x] 3.1 Add inline `<style>` in `base.html` `<head>` with progress bar CSS (fixed position, theme-aware color, indeterminate animation keyframes) — this loads without external CSS dependency
    - _Requirements: 6.3, 6.4, 8.1_
  - [x] 3.2 Add `<div id="nav-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"></div>` immediately after `<body>` tag in `base.html`
    - _Requirements: 6.1, 11.3_
  - [x] 3.3 Create the progress bar controller in JS: `startProgress()`, `setProgress(percent)`, `completeProgress()` functions that animate width and manage the indeterminate state after 500ms
    - _Requirements: 6.1, 6.2, 6.5_
  - [x] 3.4 Verify progress bar is visible above all content (z-index higher than sidebar/topbar), respects dark mode, and uses `var(--primary)` color
    - _Requirements: 6.3, 6.4_

- [x] 4. Checkpoint - Ensure server-side foundation and loading states work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Build Navigation System JavaScript
  - [x] 5.1 Create `static/js/ajax-nav.js` as an IIFE module with configuration constants (timeout: 8000ms, content selector: `.page-content`)
    - _Requirements: 1.7, 10.1, 10.5_
  - [x] 5.2 Implement the click handler that intercepts same-origin link clicks, excluding: external links, `data-full-reload` links, `target=_blank`, `data-bs-toggle` (Bootstrap modals/dropdowns), `#` anchors, and links inside modals
    - _Requirements: 1.1, 1.5_
  - [x] 5.3 Implement the `navigate(url)` function: show progress bar, show skeleton, fetch with fragment headers, handle timeout (8s), swap content on success, fallback to `window.location.href` on failure
    - _Requirements: 1.1, 1.4, 1.6_
  - [x] 5.4 Implement History API integration: `pushState` on successful navigation, `popstate` listener for back/forward that restores from cache or re-fetches
    - _Requirements: 1.2, 1.3_
  - [x] 5.5 Implement post-navigation initialization: call `lucide.createIcons()`, execute inline `<script>` tags from the fragment response, update sidebar `.active` class based on current URL
    - _Requirements: 1.6_
  - [x] 5.6 Implement the existing page-transition replacement: remove the `180ms setTimeout` page-transitioning logic for AJAX-eligible links (keep it for full-reload links as fallback)
    - _Requirements: 1.1_
  - [x] 5.7 Add `aria-busy` attribute management on `.page-content` during loading, and move focus to the first `<h5>` or `<h4>` heading in the new content after navigation completes
    - _Requirements: 11.1, 11.2, 11.5_
  - [ ]* 5.8 Write property test for URL-State Consistency
    - **Property 3: URL-State Consistency**
    - **Validates: Requirements 1.2, 3.3, 4.3**
  - [ ]* 5.9 Write property test for Fallback on Failure
    - **Property 9: Fallback on Failure**
    - **Validates: Requirements 1.4**
  - [ ]* 5.10 Write property test for Accessibility Loading State
    - **Property 10: Accessibility Loading State**
    - **Validates: Requirements 11.1, 11.2, 11.4**

- [x] 6. Build Content Cache (LRU)
  - [x] 6.1 Implement LRU cache as a `Map`-based class with `get(url)`, `set(url, {html, title, timestamp})`, `has(url)`, `invalidate(pattern)`, and `clear()` methods
    - _Requirements: 9.1, 9.6_
  - [x] 6.2 Enforce max size of 10 entries with LRU eviction: on `get()`, move entry to most-recent; on `set()` when full, delete the least-recent entry
    - _Requirements: 9.3, 9.4_
  - [x] 6.3 Integrate cache with navigation: check cache before fetching, store fragment after successful fetch, display cached content immediately on cache hit
    - _Requirements: 9.1, 9.2_
  - [x] 6.4 Implement cache invalidation: after any form submission to task create/edit/delete URLs, call `invalidate('/tasks/')` to remove all task-related cached entries
    - _Requirements: 9.5_
  - [x] 6.5 Ensure cache uses memory only (no localStorage/sessionStorage) and entries are accessible via the `popstate` handler for back/forward navigation
    - _Requirements: 9.6, 1.3_
  - [ ]* 6.6 Write property test for Cache Size Invariant
    - **Property 2: Cache Size Invariant**
    - **Validates: Requirements 9.3, 9.4**
  - [ ]* 6.7 Write property test for Cache Invalidation on Mutation
    - **Property 4: Cache Invalidation on Mutation**
    - **Validates: Requirements 9.5**
  - [ ]* 6.8 Write property test for Cache Round-Trip
    - **Property 7: Cache Round-Trip**
    - **Validates: Requirements 9.1, 9.2, 7.2**

- [x] 7. Build Prefetch Controller
  - [x] 7.1 Implement hover-based prefetch with 80ms debounce: on `mouseenter` of eligible links, start a timer; on `mouseleave` before 80ms, cancel; after 80ms, initiate prefetch
    - _Requirements: 7.1_
  - [x] 7.2 Limit concurrent prefetches to 2: track active prefetch count, skip if already at max
    - _Requirements: 7.3, 10.4_
  - [x] 7.3 Store prefetched content in Content_Cache with a 30-second TTL; discard entries older than 30s on access
    - _Requirements: 7.4_
  - [x] 7.4 Scope prefetching to only sidebar `.sidebar-link` elements and View_Switcher links (`.btn-group a[href]` in the view switcher area), excluding dynamic content links
    - _Requirements: 7.6_
  - [x] 7.5 Add Network Information API check: disable prefetching when `navigator.connection.effectiveType` is `slow-2g` or `2g`
    - _Requirements: 7.5_
  - [x] 7.6 On click of a prefetched link, use the already-cached content instead of making a new request (integrate with Navigation System)
    - _Requirements: 7.2_
  - [ ]* 7.7 Write property test for Prefetch Concurrency Bound
    - **Property 5: Prefetch Concurrency Bound**
    - **Validates: Requirements 7.3, 10.4**
  - [ ]* 7.8 Write property test for Prefetch TTL Expiry
    - **Property 8: Prefetch TTL Expiry**
    - **Validates: Requirements 7.4**

- [x] 8. Checkpoint - Ensure navigation, cache, and prefetch work end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. View Switcher and Scope/Filter AJAX Integration
  - [x] 9.1 Mark View Switcher links (List/Board/Calendar) with a `data-ajax-nav="view-switch"` attribute in the templates and ensure the Navigation System handles them via AJAX
    - _Requirements: 3.1_
  - [x] 9.2 Mark Scope Switcher links (My Tasks/All Tasks) with `data-ajax-nav="scope-switch"` attribute and ensure they trigger AJAX navigation
    - _Requirements: 4.1_
  - [x] 9.3 Update filter form submissions in `tasks/list.html` to use AJAX: intercept form submit events, serialize to query string, navigate via AJAX to the filtered URL
    - _Requirements: 4.2, 4.3_
  - [x] 9.4 After AJAX navigation in the tasks section, update active state classes on View Switcher and Scope Switcher buttons based on the current URL parameters
    - _Requirements: 3.2, 4.5_
  - [x] 9.5 Ensure filter/scope parameters are preserved when switching views: extract current query params and append them to the target view URL
    - _Requirements: 3.3_

- [x] 10. Cold Start Experience
  - [x] 10.1 Add a server-rendered generic skeleton block inside `<main class="page-content">` in `base.html` (wrapped in `<div id="cold-start-skeleton">`) that is visible before JS loads
    - _Requirements: 8.2, 8.4_
  - [x] 10.2 Add a `DOMContentLoaded` handler that removes `#cold-start-skeleton` once the page content has rendered (handles cold starts where server-rendered content arrives with the full HTML)
    - _Requirements: 8.3_
  - [x] 10.3 Ensure the inline progress bar CSS from Task 3 starts in a partially-filled state on initial page load (set width to 30% via inline style, then JS completes it on DOMContentLoaded)
    - _Requirements: 8.1_

- [x] 11. Integration Testing and Polish
  - [ ]* 11.1 Test full navigation cycle: sidebar click → skeleton shows → content loads → URL updates → back button restores previous content
    - _Requirements: 1.1, 1.2, 1.3, 5.1_
  - [ ]* 11.2 Test view switcher cycle: List → Board → Calendar with filters active → verify filters preserved, skeletons show correctly for each layout
    - _Requirements: 3.1, 3.3, 5.2_
  - [ ]* 11.3 Test failure scenarios: disconnect network during navigation → verify fallback to full-page redirect after 8s timeout
    - _Requirements: 1.4_
  - [ ]* 11.4 Test cold start scenario: clear browser cache, first load → verify progress bar and skeleton appear immediately before content renders
    - _Requirements: 8.1, 8.2_
  - [x] 11.5 Verify bundle sizes: `ajax-nav.js` < 15KB minified, `skeleton.css` < 5KB
    - _Requirements: 10.1, 10.2_
  - [ ]* 11.6 Test dark mode: verify skeletons and progress bar adapt colors correctly in both light and dark modes
    - _Requirements: 5.5, 6.4_
  - [ ]* 11.7 Test accessibility: verify `aria-busy` states toggle correctly, progress bar has proper role/aria attributes, focus moves to heading after navigation, skeleton has `aria-hidden="true"`
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  - [x] 11.8 Load the `ajax-nav.js` script with `defer` in `base.html` and verify it does not block initial page render
    - _Requirements: 10.1_

- [x] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation uses vanilla JavaScript with no build tools or third-party dependencies
- All optimizations must operate within Render/Neon/Cloudinary free-tier constraints

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "2.2", "2.3", "3.1"] },
    { "id": 2, "tasks": ["1.3", "2.4", "2.5", "3.2"] },
    { "id": 3, "tasks": ["1.4", "3.3", "3.4"] },
    { "id": 4, "tasks": ["1.5", "1.6", "5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "6.1"] },
    { "id": 6, "tasks": ["5.4", "5.5", "5.6", "6.2"] },
    { "id": 7, "tasks": ["5.7", "6.3", "6.4", "6.5", "7.1"] },
    { "id": 8, "tasks": ["5.8", "5.9", "5.10", "6.6", "6.7", "6.8", "7.2", "7.3"] },
    { "id": 9, "tasks": ["7.4", "7.5", "7.6"] },
    { "id": 10, "tasks": ["7.7", "7.8", "9.1", "9.2"] },
    { "id": 11, "tasks": ["9.3", "9.4", "9.5"] },
    { "id": 12, "tasks": ["10.1", "10.2", "10.3"] },
    { "id": 13, "tasks": ["11.1", "11.2", "11.3", "11.4", "11.5", "11.6", "11.7", "11.8"] }
  ]
}
```

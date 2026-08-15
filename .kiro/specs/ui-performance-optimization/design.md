# Design Document: UI Performance Optimization

## Overview

This design transforms the CSG Task Management System from a full-page-reload application to one that performs AJAX-based partial page updates, with skeleton loading states and intelligent prefetching. The approach uses vanilla JavaScript (no frameworks, no build tools) and a Django template mixin to return content fragments. All optimizations respect free-tier constraints (Render, Neon PostgreSQL, Cloudinary).

## Architecture

### High-Level Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│  Browser (Client-Side)                                    │
│                                                           │
│  ┌─────────────────┐  ┌──────────────────┐               │
│  │ Navigation      │  │ Loading State    │               │
│  │ System          │──│ Manager          │               │
│  │ (ajax-nav.js)   │  │ (loading.js+css) │               │
│  └────────┬────────┘  └──────────────────┘               │
│           │                                               │
│  ┌────────┴────────┐  ┌──────────────────┐               │
│  │ Content Cache   │  │ Prefetch         │               │
│  │ (LRU, 10 items) │  │ Controller       │               │
│  └─────────────────┘  └──────────────────┘               │
└──────────────────────────────────────────────────────────┘
                         │ HTTP (X-Fragment: true)
                         ▼
┌──────────────────────────────────────────────────────────┐
│  Django Server                                            │
│                                                           │
│  ┌─────────────────────────────────────────┐              │
│  │ FragmentResponseMixin                    │              │
│  │ (added to all existing CBVs)             │              │
│  │                                          │              │
│  │ Detects X-Fragment header → returns      │              │
│  │ only {% block content %} + extra_js      │              │
│  │ + X-Page-Title header                    │              │
│  └─────────────────────────────────────────┘              │
│                                                           │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │ Existing Views   │  │ File-based Cache │              │
│  │ (unchanged logic)│  │ (300s TTL)       │              │
│  └──────────────────┘  └──────────────────┘              │
└──────────────────────────────────────────────────────────┘
```

### Request Flow

1. User clicks a sidebar/view-switcher link
2. `Navigation_System` intercepts the click event
3. `Loading_State_Manager` shows Top_Progress_Bar + Skeleton for target page type
4. `Navigation_System` checks `Content_Cache` for a valid entry
   - If found: display cached content immediately, optionally revalidate
   - If not found: fetch from server with `X-Fragment: true` header
5. Server's `FragmentResponseMixin` detects the header
6. View renders normally, mixin extracts `{% block content %}` output + scripts
7. Returns fragment HTML + `X-Page-Title` response header
8. Client replaces `<main class="page-content">` innerHTML
9. Re-initializes Lucide icons, executes inline scripts
10. Updates browser URL via `history.pushState()`
11. Stores fragment in `Content_Cache`
12. `Loading_State_Manager` hides skeleton, shows content with fade-in

## Detailed Design

### 1. FragmentResponseMixin (Server-Side)

**File:** `core/mixins.py`

```python
from django.http import HttpResponse
from django.template.response import TemplateResponse


class FragmentResponseMixin:
    """
    Mixin for Django CBVs that returns only the content block
    when the request includes X-Fragment: true header.
    """
    
    def render_to_response(self, context, **response_kwargs):
        if self._is_fragment_request():
            return self._render_fragment(context, **response_kwargs)
        return super().render_to_response(context, **response_kwargs)
    
    def _is_fragment_request(self):
        return (
            self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            and self.request.headers.get('X-Fragment') == 'true'
        )
    
    def _render_fragment(self, context, **response_kwargs):
        # Use a fragment-only base template that renders just content + scripts
        original_template = self.get_template_names()
        context['is_fragment'] = True
        
        response = TemplateResponse(
            self.request,
            original_template,
            context,
            **response_kwargs
        )
        response.render()
        
        # Extract content between markers injected by fragment base template
        content = response.content.decode('utf-8')
        
        # Add page title header
        page_title = context.get('page_title', '')
        response['X-Page-Title'] = page_title
        response['X-Fragment-Response'] = 'true'
        
        return response
```

**Template strategy:** Instead of parsing HTML, we use a conditional base template approach:

```html
<!-- templates/base_fragment.html -->
{% block content %}{% endblock %}
{% block extra_js %}{% endblock %}
```

Views will use `{% extends is_fragment|yesno:"base_fragment.html,base.html" %}` or the mixin will swap the template's parent at render time.

**Simpler approach — middleware-based extraction:** A middleware that post-processes the response to extract content between HTML comment markers (`<!-- FRAGMENT_START -->` and `<!-- FRAGMENT_END -->`) placed in base.html around the content block.

### 2. Navigation System (Client-Side)

**File:** `static/js/ajax-nav.js` (target: < 15KB minified)

```javascript
// Core module structure (IIFE, no dependencies)
(function() {
  'use strict';
  
  const NAV_CONFIG = {
    contentSelector: '.page-content',
    fragmentHeaders: {
      'X-Requested-With': 'XMLHttpRequest',
      'X-Fragment': 'true'
    },
    timeout: 8000,
    cacheMaxSize: 10,
    cacheTTL: 30000, // for prefetch entries
    prefetchDelay: 80,
    maxConcurrentPrefetch: 2,
  };
  
  // --- Content Cache (LRU) ---
  const cache = new Map(); // URL -> { html, timestamp, title }
  
  function cacheGet(url) { /* LRU get */ }
  function cacheSet(url, data) { /* LRU set with eviction */ }
  function cacheInvalidatePattern(pattern) { /* invalidate task pages */ }
  
  // --- Navigation ---
  function navigate(url, options = {}) {
    // 1. Show loading state
    // 2. Check cache
    // 3. Fetch or use cached
    // 4. Swap content
    // 5. Update URL
    // 6. Re-init scripts
  }
  
  function handleClick(e) {
    // Determine if link should use AJAX nav
    // Exclude: external, data-full-reload, target=_blank, modal toggles
  }
  
  function handlePopState(e) {
    // Restore from cache or re-fetch
  }
  
  // --- Prefetch Controller ---
  let activePrefetches = 0;
  
  function handleLinkHover(e) {
    // Debounce 80ms, check eligibility, prefetch if < max
  }
  
  // --- Init ---
  function init() {
    document.addEventListener('click', handleClick);
    window.addEventListener('popstate', handlePopState);
    // Attach hover listeners to sidebar + view switcher links
  }
  
  document.addEventListener('DOMContentLoaded', init);
})();
```

### 3. Loading State Manager

**File:** `static/js/loading.js` (included in ajax-nav.js or separate small file)
**File:** `static/css/skeleton.css`

**Skeleton templates** are defined as `<template>` elements in `base.html` or as JS-generated HTML strings:

```html
<!-- In base.html, hidden templates -->
<template id="skeleton-task-list">
  <div class="skeleton-row" aria-hidden="true">
    <div class="skeleton-line skeleton-w-20"></div>
    <div class="skeleton-line skeleton-w-60"></div>
    <div class="skeleton-line skeleton-w-30"></div>
  </div>
  <!-- Repeat 5-8 rows -->
</template>

<template id="skeleton-kanban">
  <div class="skeleton-board" aria-hidden="true">
    <div class="skeleton-column">...</div>
    <div class="skeleton-column">...</div>
    <div class="skeleton-column">...</div>
  </div>
</template>
```

**CSS skeleton animations:**

```css
.skeleton-line {
  background: var(--skeleton-bg, #e2e8f0);
  border-radius: 4px;
  height: 14px;
  margin-bottom: 8px;
  animation: skeleton-shimmer 1.5s infinite ease-in-out;
}

[data-mode="dark"] .skeleton-line {
  --skeleton-bg: #334155;
}

@keyframes skeleton-shimmer {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}
```

### 4. Top Progress Bar

Implemented as a fixed-position div injected at page load:

```html
<!-- Inline in base.html <head> for cold-start visibility -->
<style>
  #nav-progress{position:fixed;top:0;left:0;width:0;height:3px;
    background:var(--primary,#FF4FA3);z-index:99999;
    transition:width .3s ease;pointer-events:none}
  #nav-progress.active{animation:progress-indeterminate 1.5s infinite}
  @keyframes progress-indeterminate{
    0%{width:0;left:0}50%{width:60%}100%{width:100%;left:100%}}
</style>
<div id="nav-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"></div>
```

### 5. Cold Start Inline Skeleton

Server-rendered skeleton in `base.html` that is visible before JS loads:

```html
<main class="page-content">
  <!-- Cold-start skeleton: visible until JS replaces with actual content -->
  <div id="cold-start-skeleton" aria-hidden="true">
    <div class="skeleton-line skeleton-w-40" style="height:24px;margin-bottom:16px"></div>
    <div class="skeleton-line skeleton-w-100"></div>
    <div class="skeleton-line skeleton-w-80"></div>
    <div class="skeleton-line skeleton-w-90"></div>
  </div>
  {% block content %}{% endblock %}
</main>
```

JavaScript removes `#cold-start-skeleton` on DOMContentLoaded.

### 6. Fragment Marker Approach (chosen over template swapping)

In `base.html`, wrap the content block with HTML comments:

```html
<!-- FRAGMENT_START -->
<main class="page-content">
  {% block content %}{% endblock %}
</main>
<!-- FRAGMENT_END -->

<!-- FRAGMENT_SCRIPTS_START -->
{% block extra_js %}{% endblock %}
<!-- FRAGMENT_SCRIPTS_END -->
```

The `FragmentResponseMixin` post-processes the rendered HTML to extract only the content between these markers. This avoids the complexity of template inheritance manipulation.

### 7. Integration Points

**Existing views — changes required:**

All primary views get the mixin added as a parent class:
- `DashboardView(FragmentResponseMixin, LoginRequiredMixin, TemplateView)`
- `TaskListView(FragmentResponseMixin, LoginRequiredMixin, ListView)`
- `TaskBoardView(FragmentResponseMixin, LoginRequiredMixin, TemplateView)`
- `TaskCalendarView(FragmentResponseMixin, LoginRequiredMixin, TemplateView)`
- `OfficerListView(FragmentResponseMixin, LoginRequiredMixin, ListView)`
- `NotificationListView(FragmentResponseMixin, LoginRequiredMixin, ListView)`
- `ReportsDashboardView(FragmentResponseMixin, LoginRequiredMixin, TemplateView)`

**Existing page transition JS — changes required:**

The current `180ms setTimeout` + `body.page-transitioning` class in `base.html` is replaced by the AJAX navigation system. The fade class is removed for AJAX-navigated links, and retained only as a fallback for full-page navigations.

**sidebar active state:**

After AJAX navigation, the client-side code updates the `.sidebar-link.active` class based on the new URL pathname matching link href patterns.

## File Structure

```
static/
├── js/
│   ├── ajax-nav.js        (Navigation System + Prefetch + Cache)
│   ├── loading.js         (Loading State Manager, or merged into ajax-nav.js)
│   ├── lucide.min.js      (existing)
│   └── table-sort.js      (existing)
├── css/
│   ├── style.css          (existing)
│   └── skeleton.css       (Skeleton + progress bar styles)
core/
├── mixins.py              (FragmentResponseMixin - NEW)
templates/
├── base.html              (add fragment markers, progress bar, skeleton templates)
├── skeletons/
│   ├── _task_list.html    (task list skeleton partial)
│   ├── _kanban.html       (board skeleton partial)
│   ├── _calendar.html     (calendar skeleton partial)
│   ├── _dashboard.html    (dashboard skeleton partial)
│   ├── _officers.html     (officers list skeleton partial)
│   └── _notifications.html (notifications skeleton partial)
```

## Components and Interfaces

### FragmentResponseMixin (Server-Side Component)

| Attribute | Description |
|-----------|-------------|
| **Module** | `core/mixins.py` |
| **Type** | Django class-based view mixin |
| **Interface** | Overrides `render_to_response(context, **kwargs)` |
| **Input** | HTTP request with optional `X-Fragment: true` and `X-Requested-With: XMLHttpRequest` headers |
| **Output** | Full HTML response (standard) or fragment HTML with `X-Page-Title` and `X-Fragment-Response` headers |

**Public Methods:**
- `render_to_response(context, **kwargs)` — Delegates to `_render_fragment()` or `super()` based on request headers.
- `_is_fragment_request()` → `bool` — Returns `True` if both AJAX headers are present.
- `_render_fragment(context, **kwargs)` → `HttpResponse` — Extracts content between `<!-- FRAGMENT_START -->` and `<!-- FRAGMENT_END -->` markers plus scripts between `<!-- FRAGMENT_SCRIPTS_START -->` and `<!-- FRAGMENT_SCRIPTS_END -->`.

### Navigation System (Client-Side Component)

| Attribute | Description |
|-----------|-------------|
| **Module** | `static/js/ajax-nav.js` |
| **Type** | IIFE module (vanilla JavaScript) |
| **Interface** | Event-driven (click, popstate, mouseenter) |

**Public API (exposed via `window.CSGNav` for external use):**
- `navigate(url: string, options?: {replace?: boolean, skipCache?: boolean})` → `Promise<void>` — Programmatic navigation.
- `invalidateCache(pattern?: string)` → `void` — Clears cache entries matching a URL pattern.
- `prefetch(url: string)` → `Promise<void>` — Manually prefetch a URL.

**Internal Functions:**
- `handleClick(event: MouseEvent)` → intercepts link clicks
- `handlePopState(event: PopStateEvent)` → handles back/forward navigation
- `handleLinkHover(event: MouseEvent)` → triggers prefetch after debounce

### Content Cache (Client-Side Component)

| Attribute | Description |
|-----------|-------------|
| **Module** | Internal to `ajax-nav.js` |
| **Type** | LRU cache (Map-based) |
| **Capacity** | 10 entries maximum |

**Interface:**
- `cacheGet(url: string)` → `{html: string, title: string, timestamp: number} | null`
- `cacheSet(url: string, data: {html: string, title: string})` → `void`
- `cacheInvalidatePattern(pattern: string | RegExp)` → `void`

### Loading State Manager (Client-Side Component)

| Attribute | Description |
|-----------|-------------|
| **Module** | `static/js/loading.js` (or inlined in `ajax-nav.js`) |
| **Type** | Singleton module |

**Public API:**
- `showSkeleton(targetType: string, containerEl: HTMLElement)` → `void` — Shows appropriate skeleton for page type.
- `hideSkeleton(containerEl: HTMLElement)` → `void` — Replaces skeleton with content using fade-in.
- `showProgressBar()` → `void` — Activates top progress bar animation.
- `hideProgressBar()` → `void` — Completes and fades out progress bar.
- `setAriaBusy(containerEl: HTMLElement, busy: boolean)` → `void` — Manages aria-busy state.

### Prefetch Controller (Client-Side Component)

| Attribute | Description |
|-----------|-------------|
| **Module** | Internal to `ajax-nav.js` |
| **Type** | Debounced hover handler with concurrency control |

**Interface:**
- `handleLinkHover(event: MouseEvent)` → `void` — Debounces 80ms, checks eligibility, initiates prefetch.
- `isEligible(linkEl: HTMLAnchorElement)` → `boolean` — Returns true for sidebar/view-switcher links only.
- `getActivePrefetchCount()` → `number` — Current in-flight prefetch count (max 2).

## Data Models

This feature does not introduce new database models or modify existing ones. All data structures are client-side in-memory objects.

### Client-Side Data Structures

#### Cache Entry

```typescript
interface CacheEntry {
  html: string;        // Fragment HTML content
  title: string;       // Page title from X-Page-Title header
  timestamp: number;   // Date.now() when stored
  scripts: string;     // Extracted script content from extra_js block
}
```

#### Navigation State (History API)

```typescript
interface NavigationState {
  url: string;         // Full URL including query params
  scrollY: number;     // Scroll position at time of navigation
  cacheKey: string;    // Cache lookup key (URL with query params)
}
```

#### Prefetch Queue Item

```typescript
interface PrefetchItem {
  url: string;           // Target URL to prefetch
  abortController: AbortController;  // For cancellation
  timestamp: number;     // When prefetch was initiated
}
```

### Response Headers (Fragment Requests)

| Header | Value | Direction |
|--------|-------|-----------|
| `X-Requested-With` | `XMLHttpRequest` | Request |
| `X-Fragment` | `true` | Request |
| `X-Page-Title` | Page title string | Response |
| `X-Fragment-Response` | `true` | Response |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Fragment Subset

*For any* Django view using FragmentResponseMixin, the HTML content returned in a fragment response SHALL be a strict subset of the corresponding full-page response content, and SHALL include any script content from the `{% block extra_js %}` block.

**Validates: Requirements 2.1, 2.2, 2.5**

### Property 2: Cache Size Invariant

*For any* sequence of cache insertions (regardless of count or order), the Content_Cache size SHALL never exceed 10 entries, and when at capacity the least-recently-used entry SHALL be the one evicted.

**Validates: Requirements 9.3, 9.4**

### Property 3: URL-State Consistency

*For any* completed AJAX navigation (including view switches and filter changes), `window.location.href` SHALL match the target URL including all query parameters, and for any sequence of N navigations, pressing back N times SHALL restore the URL from N navigations ago.

**Validates: Requirements 1.2, 3.3, 4.3**

### Property 4: Cache Invalidation on Mutation

*For any* data-modifying action (task create, edit, or delete), all Content_Cache entries whose URL matches the `/tasks/` pattern SHALL be removed, while entries for non-task URLs SHALL be preserved.

**Validates: Requirements 9.5**

### Property 5: Prefetch Concurrency Bound

*For any* number of simultaneous link hover events, the number of in-flight prefetch requests SHALL never exceed 2 at any point in time.

**Validates: Requirements 7.3, 10.4**

### Property 6: No Additional Database Queries

*For any* view with FragmentResponseMixin, the number of database queries executed for a fragment request SHALL equal the number executed for a full-page request of the same URL with identical parameters.

**Validates: Requirements 10.3**

### Property 7: Cache Round-Trip

*For any* URL successfully fetched via AJAX navigation, the Content_Cache SHALL store the fragment content, and a subsequent navigation to the same URL (within TTL) SHALL retrieve the identical content without making a new network request.

**Validates: Requirements 9.1, 9.2, 7.2**

### Property 8: Prefetch TTL Expiry

*For any* prefetched cache entry, accessing it after 30 seconds have elapsed SHALL result in a cache miss, forcing a fresh network request.

**Validates: Requirements 7.4**

### Property 9: Fallback on Failure

*For any* AJAX navigation request that fails or exceeds the 8-second timeout, the Navigation_System SHALL fall back to a traditional full-page navigation to the target URL.

**Validates: Requirements 1.4**

### Property 10: Accessibility Loading State

*For any* AJAX navigation lifecycle, the content container SHALL have `aria-busy="true"` while loading and `aria-busy="false"` when complete, and all skeleton elements SHALL have `aria-hidden="true"` at all times they are visible.

**Validates: Requirements 11.1, 11.2, 11.4**

## Error Handling

### Network Failures

| Scenario | Behavior |
|----------|----------|
| Fetch request fails (network error) | Fall back to full-page navigation via `window.location.href = targetUrl` |
| Request timeout (8 seconds) | Abort fetch via AbortController, fall back to full-page navigation |
| HTTP 4xx/5xx response | Fall back to full-page navigation (server handles error pages) |
| Prefetch failure | Silently discard; no user-visible error. Navigation will fetch fresh on click |

### Content Parsing Failures

| Scenario | Behavior |
|----------|----------|
| Fragment markers not found in response | Treat as non-fragment response, fall back to full-page navigation |
| Empty fragment content | Fall back to full-page navigation |
| Script execution error in loaded content | Log to console, do not block content display |

### Cache Errors

| Scenario | Behavior |
|----------|----------|
| Cache storage fails (e.g., quota) | Continue without caching; navigation still works |
| Cached content is corrupted/empty | Remove entry, fetch fresh content |

### Server-Side Error Handling

| Scenario | Behavior |
|----------|----------|
| Template rendering error in fragment mode | Django's standard error handling applies; returns 500 which triggers client fallback |
| Missing `page_title` in context | Return empty `X-Page-Title` header; client uses fallback title from `<title>` tag |
| Mixin applied to non-TemplateResponse view | `render_to_response` is not called; mixin is a no-op |

### Graceful Degradation

The entire AJAX navigation system is a progressive enhancement. If JavaScript fails to load or execute:
- All links remain standard `<a>` elements with valid `href` attributes
- Full-page navigation works exactly as before
- Server always renders complete pages for non-fragment requests
- No functionality is lost, only the performance optimization

## Testing Strategy

### Unit Tests (Example-Based)

Unit tests cover specific behaviors, edge cases, and integration points:

- **FragmentResponseMixin**: Test that fragment requests return only content block, standard requests return full page, `X-Page-Title` header is present, scripts are included.
- **Cache operations**: Test LRU eviction order with specific sequences, TTL expiry with mocked timers.
- **Navigation eligibility**: Test that external links, `data-full-reload` links, and modal triggers are excluded.
- **Skeleton mapping**: Test that each page type (list, board, calendar, dashboard, officers, notifications) gets the correct skeleton template.
- **Cold-start skeleton removal**: Test that `#cold-start-skeleton` is removed on DOMContentLoaded.
- **Accessibility attributes**: Test aria-busy toggling and aria-hidden on skeletons.
- **Focus management**: Test focus moves to main heading after navigation.

### Property-Based Tests

Property-based tests verify universal correctness properties across many generated inputs:

- **Library**: Hypothesis (Python, for server-side) + fast-check (JavaScript, for client-side)
- **Minimum iterations**: 100 per property test
- **Tag format**: `Feature: ui-performance-optimization, Property N: <property_text>`

| Property | Test Approach |
|----------|--------------|
| P1: Fragment Subset | Generate random view contexts, compare fragment vs full response content |
| P2: Cache Size Invariant | Generate random sequences of cache insertions (50-200 ops), assert size ≤ 10 after each |
| P3: URL-State Consistency | Generate random navigation sequences with varying query params, verify URL after each |
| P4: Cache Invalidation on Mutation | Generate random cache states (mix of task/non-task URLs), trigger mutation, verify correct entries removed |
| P5: Prefetch Concurrency Bound | Generate rapid bursts of hover events, assert active count ≤ 2 at every observation point |
| P6: No Additional DB Queries | Generate random view/parameter combinations, compare query counts between fragment and full requests |
| P7: Cache Round-Trip | Generate random URLs and content, store in cache, retrieve and compare |
| P8: Prefetch TTL Expiry | Generate random cache entries with varying ages, verify expired entries return cache miss |
| P9: Fallback on Failure | Generate random failure types (timeout, network error, 5xx), verify fallback navigation triggered |
| P10: Accessibility Loading State | Generate random navigation sequences, verify aria-busy and aria-hidden at each lifecycle point |

### Integration Tests

- Full request cycle: browser click → AJAX fetch → fragment response → content swap → URL update
- Back/forward navigation across multiple pages
- Filter + view switch combination flows
- Cold-start to warm-navigation transition
- Concurrent prefetch + navigation race conditions

### Performance Tests

- Verify `ajax-nav.js` minified size < 15KB
- Verify `skeleton.css` size < 5KB
- Measure and assert fragment response time < full-page response time for each view
- Verify no additional DB queries via Django's `assertNumQueries`

## Performance Considerations

- **Bundle size:** Single `ajax-nav.js` file < 15KB keeps the added download minimal. No npm/webpack needed.
- **Server load:** Fragment responses are slightly smaller (skip base template HTML ~4-8KB), reducing bandwidth. No extra DB queries.
- **Prefetch budget:** Max 2 concurrent prefetches + 30s TTL prevents excessive server requests while still providing perceived speed gains on the most likely next navigations.
- **Cache memory:** 10 entries × ~20-50KB average page = 200-500KB max memory overhead, acceptable for modern browsers.
- **Cold start mitigation:** Inline CSS progress bar + server-rendered skeleton gives immediate feedback within the first paint, before any JS or external CSS loads.
- **Connection awareness:** Prefetching disabled on slow connections (Network Information API) prevents wasting limited mobile data.

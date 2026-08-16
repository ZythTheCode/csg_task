# Requirements Document

## Introduction

This feature optimizes the perceived performance and responsiveness of the CSG Task Management System's UI and backend. The system is a server-side rendered Django application deployed on Render free tier with Neon PostgreSQL and Cloudinary free tier storage. Current navigation relies entirely on full-page reloads with an artificial 180ms fade delay, and provides no visual feedback during data loading. This optimization introduces AJAX-based partial page updates for same-section navigation, skeleton loading states, intelligent prefetching, server-side query optimization, and strategic caching — all within the constraints of vanilla JavaScript, no build tools, and free-tier hosting limits.

## Glossary

- **Navigation_System**: The client-side JavaScript module responsible for intercepting navigation clicks and determining whether to perform a full-page reload or an AJAX partial content swap.
- **Loading_State_Manager**: The client-side JavaScript module responsible for showing and hiding skeleton placeholders, spinners, and progress indicators during content loading.
- **Content_Fragment_View**: A Django view that returns only the main page content HTML (without base template chrome) when requested via an AJAX header, enabling partial page updates.
- **Prefetch_Controller**: The client-side JavaScript module that speculatively fetches page content on link hover or visibility to reduce perceived navigation time.
- **Skeleton_Placeholder**: A lightweight HTML/CSS element that mimics the layout shape of content being loaded, providing visual feedback before actual data renders.
- **Top_Progress_Bar**: A thin animated bar at the top of the viewport indicating an in-progress page load or AJAX request.
- **View_Switcher**: The UI component (List/Board/Calendar tabs) that allows switching between task views within the tasks section.
- **Scope_Switcher**: The UI component (My Tasks/All Tasks toggle) that switches between personal and organizational task scopes.
- **Filter_Panel**: The UI section containing task filters (status, priority, category, officer) that refine displayed results.
- **Cold_Start**: The initial server response delay (2-5 seconds) caused by Render free tier spinning up the application after inactivity.
- **Content_Cache**: The client-side in-memory storage that holds recently fetched page fragments to enable instant back-navigation.
- **Query_Optimizer**: The server-side Django queryset optimization layer that ensures database queries use appropriate select_related, prefetch_related, indexing, and caching strategies.
- **View_Cache**: The server-side Django cache layer that stores computed view data (aggregated counts, officer lists, frequently accessed querysets) to reduce database round-trips.

## Requirements

### Requirement 1: AJAX Partial Page Navigation

**User Story:** As an officer, I want navigation between pages within the app to load only the changed content area, so that page transitions feel faster and the sidebar/topbar remain stable.

#### Acceptance Criteria

1. WHEN a sidebar navigation link is clicked, THE Navigation_System SHALL fetch only the page content fragment via AJAX and replace the main content area without a full-page reload.
2. WHEN a same-section navigation link is clicked and the AJAX request completes, THE Navigation_System SHALL update the browser URL using the History API to reflect the new page.
3. WHEN the browser back or forward button is pressed, THE Navigation_System SHALL restore the previous page content from the Content_Cache or re-fetch the content fragment.
4. IF an AJAX navigation request fails or times out after 8 seconds, THEN THE Navigation_System SHALL fall back to a traditional full-page navigation to the target URL.
5. WHEN a navigation link points to an external domain or has the attribute `data-full-reload`, THE Navigation_System SHALL perform a traditional full-page navigation.
6. WHEN partial content is loaded via AJAX, THE Navigation_System SHALL re-initialize Lucide icons and any page-specific JavaScript within the new content area.
7. THE Navigation_System SHALL use a custom HTTP header (`X-Requested-With: XMLHttpRequest` and `X-Fragment: true`) to signal content-only responses from the server.

### Requirement 2: Content Fragment Responses from Django Views

**User Story:** As a developer, I want Django views to detect AJAX fragment requests and return only the page content block, so that the client can perform partial page updates without downloading the full HTML document.

#### Acceptance Criteria

1. WHEN a request includes both `X-Requested-With: XMLHttpRequest` and `X-Fragment: true` headers, THE Content_Fragment_View SHALL render and return only the content within the `{% block content %}` template block, excluding the base template layout.
2. WHEN a standard (non-fragment) request is received, THE Content_Fragment_View SHALL render the full page including the base template as before.
3. THE Content_Fragment_View SHALL include a response header `X-Page-Title` containing the page title so the client can update the document title and breadcrumb.
4. THE Content_Fragment_View SHALL be implemented as a Django mixin that can be added to existing class-based views without modifying their core logic.
5. WHEN a fragment response is returned, THE Content_Fragment_View SHALL include necessary inline `<script>` tags from the `{% block extra_js %}` template block so page-specific JavaScript is executed.

### Requirement 3: View Switcher Partial Loading (List/Board/Calendar)

**User Story:** As an officer, I want switching between List, Board, and Calendar views to load instantly without a full-page reload, so that I can quickly compare different task visualizations.

#### Acceptance Criteria

1. WHEN a View_Switcher tab is clicked (List, Board, or Calendar), THE Navigation_System SHALL load the target view content via AJAX and replace only the main content area.
2. WHEN the view switch completes, THE Navigation_System SHALL update the active state of the View_Switcher tabs to reflect the current view.
3. WHEN switching views, THE Navigation_System SHALL preserve the current filter and scope parameters in the URL and pass them to the AJAX request.
4. WHILE a view switch is in progress, THE Loading_State_Manager SHALL display a Skeleton_Placeholder matching the target view layout (list rows, kanban columns, or calendar grid).

### Requirement 4: Scope and Filter Application Without Full Reload

**User Story:** As an officer, I want changing task scope (My Tasks/All Tasks) and applying filters to update results inline, so that I do not lose my scroll position or context.

#### Acceptance Criteria

1. WHEN the Scope_Switcher is toggled between My Tasks and All Tasks, THE Navigation_System SHALL fetch updated task content via AJAX and replace the task listing area.
2. WHEN a filter is applied or removed in the Filter_Panel, THE Navigation_System SHALL fetch updated results via AJAX and replace the task listing area.
3. WHEN filters or scope are changed, THE Navigation_System SHALL update the browser URL query parameters to reflect the current filter state.
4. WHILE filtered results are loading, THE Loading_State_Manager SHALL display a Skeleton_Placeholder in the task listing area.
5. WHEN scope or filters change, THE Navigation_System SHALL update the active states of the Scope_Switcher and Filter_Panel to reflect current selections.

### Requirement 5: Skeleton Loading States

**User Story:** As an officer, I want to see placeholder shapes where content will appear during loading, so that I understand the page layout and know that data is being fetched.

#### Acceptance Criteria

1. WHILE page content is loading via AJAX navigation, THE Loading_State_Manager SHALL display Skeleton_Placeholder elements that match the expected content layout of the target page.
2. THE Loading_State_Manager SHALL provide distinct Skeleton_Placeholder templates for: task list rows, kanban board columns, calendar grid, dashboard stat cards, officer list items, and notification items.
3. WHEN content finishes loading, THE Loading_State_Manager SHALL replace the Skeleton_Placeholder with the actual content using a brief fade-in transition of no more than 150 milliseconds.
4. THE Skeleton_Placeholder elements SHALL use CSS animation (pulse or shimmer) to indicate active loading rather than appearing as static gray blocks.
5. THE Skeleton_Placeholder elements SHALL respect the current theme (light/dark mode) by using appropriate background colors derived from CSS custom properties.

### Requirement 6: Top Progress Bar

**User Story:** As an officer, I want a visible progress indicator at the top of the page during any loading operation, so that I always know something is happening even if the content area is out of view.

#### Acceptance Criteria

1. WHEN any AJAX navigation request begins, THE Loading_State_Manager SHALL display the Top_Progress_Bar at the top of the viewport with an animated fill from left to right.
2. WHEN the AJAX navigation request completes (success or failure), THE Loading_State_Manager SHALL animate the Top_Progress_Bar to 100% and then fade it out within 300 milliseconds.
3. THE Top_Progress_Bar SHALL be fixed to the top of the viewport and visible above all other content with a z-index higher than the topbar.
4. THE Top_Progress_Bar SHALL use the current theme's primary color via CSS custom properties.
5. IF a navigation request takes longer than 500 milliseconds, THEN THE Top_Progress_Bar SHALL display an indeterminate animation pattern to indicate continued activity.

### Requirement 7: Link Prefetching on Hover

**User Story:** As an officer, I want pages to begin loading when I hover over navigation links, so that the page appears to load instantly when I click.

#### Acceptance Criteria

1. WHEN the user hovers over a prefetch-eligible navigation link for more than 80 milliseconds, THE Prefetch_Controller SHALL initiate a background fetch of the content fragment for that URL.
2. WHEN a prefetched link is subsequently clicked, THE Navigation_System SHALL use the already-fetched content from the Content_Cache instead of making a new request.
3. THE Prefetch_Controller SHALL limit concurrent prefetch requests to a maximum of 2 to avoid unnecessary server load and bandwidth consumption.
4. THE Prefetch_Controller SHALL discard prefetched content from the Content_Cache after 30 seconds to prevent displaying stale data.
5. WHILE the device is on a connection the browser reports as `slow-2g` or `2g` via the Network Information API, THE Prefetch_Controller SHALL disable all prefetching to conserve bandwidth.
6. THE Prefetch_Controller SHALL only prefetch sidebar navigation links and View_Switcher links, excluding links inside dynamic content areas such as task lists and modals.

### Requirement 8: Cold Start Loading Experience

**User Story:** As an officer, I want clear visual feedback when the app is loading for the first time (cold start), so that I know the system is responding and not broken.

#### Acceptance Criteria

1. WHEN the application performs an initial full-page load, THE Loading_State_Manager SHALL display the Top_Progress_Bar immediately via inline CSS that does not depend on external stylesheet loading.
2. WHEN the initial page HTML begins rendering, THE Loading_State_Manager SHALL show Skeleton_Placeholder elements inline in the server-rendered HTML for the main content area that remain visible until JavaScript initializes.
3. WHEN the page DOM is fully loaded and JavaScript has initialized, THE Loading_State_Manager SHALL replace the inline Skeleton_Placeholder elements with the actual rendered content.
4. THE inline Skeleton_Placeholder for cold starts SHALL be rendered server-side in the Django template so it appears immediately without waiting for JavaScript execution.

### Requirement 9: Client-Side Content Cache

**User Story:** As an officer, I want previously visited pages to load instantly when I navigate back, so that navigating between sections feels instantaneous.

#### Acceptance Criteria

1. WHEN a page fragment is successfully loaded via AJAX, THE Content_Cache SHALL store the HTML content keyed by the full URL including query parameters.
2. WHEN the user navigates to a URL that exists in the Content_Cache, THE Navigation_System SHALL display the cached content immediately and optionally revalidate in the background.
3. THE Content_Cache SHALL hold a maximum of 10 page entries to limit memory consumption on resource-constrained devices.
4. THE Content_Cache SHALL evict the least-recently-used entry when the maximum capacity is reached.
5. WHEN the user performs a data-modifying action (creating, editing, or deleting a task), THE Content_Cache SHALL invalidate all cached entries for task-related pages (list, board, calendar).
6. THE Content_Cache SHALL store entries in memory only and not persist to localStorage or sessionStorage to avoid serving stale content across sessions.

### Requirement 10: Server-Side Query Optimization

**User Story:** As a developer, I want database queries to be optimized with proper relationship loading and indexing, so that page response times are minimized even on the free-tier Neon PostgreSQL database.

#### Acceptance Criteria

1. WHEN the TaskListView loads tasks, THE Query_Optimizer SHALL use select_related for single-value foreign keys (created_by, organization) and prefetch_related for many-to-many relationships (assigned_officers with officer_profile and position) in a single queryset chain.
2. WHEN the TaskBoardView builds Kanban columns, THE Query_Optimizer SHALL execute a single base queryset and partition results in Python rather than issuing separate filtered queries per status column.
3. WHEN the DashboardView computes task statistics, THE Query_Optimizer SHALL use a single aggregated query with conditional Count expressions rather than multiple individual count queries.
4. WHEN the OfficerListView loads officers with task counts, THE Query_Optimizer SHALL use annotated queries with Count aggregations rather than performing per-officer task count lookups.
5. WHEN the NotificationListView loads notifications, THE Query_Optimizer SHALL use select_related for related_task and only() to limit columns retrieved to those displayed in the list.
6. THE Query_Optimizer SHALL ensure that all queryset slicing (e.g., [:10], [:50]) is applied after all filters and ordering to leverage database-level LIMIT rather than Python-level slicing of full result sets.

### Requirement 11: Server-Side View Caching

**User Story:** As a developer, I want frequently accessed computed data (officer lists, task counts, dashboard aggregates) to be cached, so that repeated page loads do not require fresh database queries.

#### Acceptance Criteria

1. WHEN the TaskListView or TaskBoardView retrieves the officers list for filter dropdowns, THE View_Cache SHALL cache the result per organization for 60 seconds to avoid repeated queries.
2. WHEN the DashboardView computes task count aggregates, THE View_Cache SHALL cache the computed counts per user and scope for 30 seconds.
3. WHEN the notifications context processor computes the unread notification count, THE View_Cache SHALL cache the count per user for 30 seconds.
4. WHEN a data-modifying action occurs (task create, update, delete, or officer change), THE View_Cache SHALL invalidate related cache keys for the affected organization.
5. THE View_Cache SHALL use the existing file-based Django cache backend configured in settings without introducing additional cache infrastructure.
6. IF a cache read fails or returns stale data, THEN THE View_Cache SHALL fall back to a fresh database query without raising an error to the user.

### Requirement 12: Optimized Kanban Board Queries

**User Story:** As an officer, I want the Kanban Board view to load quickly even with many tasks, so that I can use the board view for daily workflow management without delays.

#### Acceptance Criteria

1. WHEN the TaskBoardView loads, THE Query_Optimizer SHALL fetch all non-archived tasks matching the current filters in a single query and partition them into status columns in application code.
2. WHEN building Kanban columns, THE Query_Optimizer SHALL limit each column to 50 tasks and provide a count of total tasks per column from the pre-fetched queryset.
3. WHEN the TaskBoardView receives a fragment request, THE Content_Fragment_View SHALL return only the board content without the full page layout to reduce payload size.
4. THE Query_Optimizer SHALL prefetch assigned officers, their profiles, and positions for all tasks in the board queryset using a single prefetch_related call.

### Requirement 13: Performance Budget and Free-Tier Constraints

**User Story:** As the system administrator, I want UI performance optimizations to operate within the free-tier resource limits of Render, Neon PostgreSQL, and Cloudinary, so that the application remains deployable at no cost.

#### Acceptance Criteria

1. THE Navigation_System JavaScript file SHALL not exceed 15 KB minified (uncompressed) to minimize download impact on first load.
2. THE Loading_State_Manager CSS (skeleton styles) SHALL not exceed 5 KB to minimize stylesheet size.
3. WHEN a Content_Fragment_View processes a fragment request, THE Content_Fragment_View SHALL not execute any additional database queries beyond those already required for the full-page render.
4. THE Prefetch_Controller SHALL not generate more than 2 speculative requests per page view to limit the request volume on the Render free tier.
5. THE Navigation_System SHALL not introduce any new third-party JavaScript dependencies beyond the existing Bootstrap 5 and Lucide icons.
6. THE Skeleton_Placeholder elements SHALL use only CSS for animation without requiring additional image assets or SVG files from Cloudinary.

### Requirement 14: Visual Stability and Graceful Degradation

**User Story:** As an officer, I want the app to remain visually stable and fully functional regardless of whether AJAX navigation succeeds or fails, so that I never encounter broken layouts, missing content, or unresponsive states.

#### Acceptance Criteria

1. IF JavaScript fails to load or execute, THEN THE Navigation_System SHALL not interfere with standard full-page navigation, and the application SHALL remain fully functional via traditional page loads.
2. WHEN an AJAX content swap occurs, THE Navigation_System SHALL ensure the replaced content area maintains its CSS layout constraints (no layout shifts, height collapses, or overflow changes).
3. IF a fragment response returns malformed HTML or an empty body, THEN THE Navigation_System SHALL discard the response and perform a full-page navigation to the target URL instead of rendering broken content.
4. WHEN the Navigation_System replaces content, THE Navigation_System SHALL remove all event listeners and timers from the previous content to prevent memory leaks and ghost interactions.
5. WHILE a navigation request is in progress, THE Navigation_System SHALL disable further navigation clicks on the same target to prevent duplicate requests and content flickering.
6. WHEN the Navigation_System re-initializes page-specific JavaScript after a content swap, THE Navigation_System SHALL wait until the new DOM is fully inserted before executing scripts to prevent null reference errors.
7. IF a skeleton placeholder is displayed for longer than 10 seconds without content loading, THEN THE Loading_State_Manager SHALL display a retry prompt or fall back to a full-page reload to prevent indefinite loading states.
8. THE Navigation_System SHALL preserve the scroll position of the sidebar and topbar during content swaps to prevent visual jumping of persistent UI elements.

### Requirement 15: Accessibility of Loading States

**User Story:** As an officer using assistive technology, I want loading states to be announced by screen readers, so that I am aware when content is being fetched and when it becomes available.

#### Acceptance Criteria

1. WHEN a loading state begins, THE Loading_State_Manager SHALL set an `aria-busy="true"` attribute on the content container being updated.
2. WHEN loading completes, THE Loading_State_Manager SHALL set `aria-busy="false"` on the content container and announce the content update via an `aria-live="polite"` region.
3. THE Top_Progress_Bar SHALL have a `role="progressbar"` attribute with appropriate `aria-valuenow`, `aria-valuemin`, and `aria-valuemax` attributes.
4. THE Skeleton_Placeholder elements SHALL have `aria-hidden="true"` to prevent screen readers from announcing meaningless placeholder content.
5. WHEN AJAX navigation completes, THE Navigation_System SHALL move focus to the main content area heading to assist keyboard navigation users.

# Requirements Document

## Introduction

This feature replaces the current server-round-trip pattern on the Tasks tab with a hybrid client-side data management approach. When a user navigates to the Tasks tab, all task data for their organization is fetched once as JSON from the server. The frontend (vanilla JS) then handles view switching (List/Board/Calendar), scope toggling (My Tasks/All Tasks), filtering, sorting, and search entirely client-side. Only CRUD operations (create, update, delete, status moves, comments, attachments) continue to hit the server, after which the local data store is patched without a full page refresh.

## Glossary

- **Task_Store**: The client-side JavaScript module responsible for holding, filtering, sorting, and exposing task data in memory
- **Data_API**: The DRF API endpoint that returns the full set of task data for the authenticated user's organization as JSON
- **View_Renderer**: The client-side module that renders task data into the active view (List, Board, or Calendar) using DOM manipulation
- **Filter_Engine**: The client-side module that applies filter criteria (status, priority, category, officer, search) to the Task_Store dataset
- **Scope_Toggle**: The UI control that switches between "My Tasks" (tasks assigned to or created by the current user) and "All Tasks" (all organization tasks)
- **CRUD_Service**: The client-side module responsible for sending create, update, and delete requests to the server and patching the Task_Store on success
- **Current_User**: The authenticated user whose ID and role information is embedded in the page context

## Requirements

### Requirement 1: Initial Data Load

**User Story:** As an officer, I want all task data to be loaded once when I open the Tasks tab, so that subsequent interactions are instant without waiting for server responses.

#### Acceptance Criteria

1. WHEN the user navigates to the Tasks tab, THE Data_API SHALL return a JSON payload containing all non-archived tasks for the Current_User's organization, limited to a maximum of 500 tasks ordered by created_at descending.
2. WHEN the Data_API response is received, THE Task_Store SHALL store the complete dataset in memory as a JavaScript array accessible for client-side filtering, sorting, and view rendering.
3. THE Data_API SHALL include for each task: id, task_number, title, description, category, priority, status, progress, due_date, completion_date, created_at, created_by (id, name), assigned_officers (list of id, name, position_title), and is_overdue flag.
4. WHILE the initial data load is in progress, THE View_Renderer SHALL display a skeleton loading state matching the task list layout, with CSS pulse animation indicating active loading.
5. IF the Data_API request fails or does not respond within 8 seconds, THEN THE View_Renderer SHALL display an error message indicating the load failure and a retry button that re-initiates the same Data_API request.
6. IF the user has the has_task_override role property (super_admin, org_admin, or president), THEN THE Data_API SHALL return all non-archived tasks for the organization. IF the user does not have has_task_override, THEN THE Data_API SHALL return only tasks where the Current_User is in assigned_officers or is the created_by user.
7. WHEN the retry button is activated after a failed load, THE View_Renderer SHALL display the skeleton loading state again and re-issue the Data_API request with identical parameters.

### Requirement 2: Client-Side View Switching

**User Story:** As an officer, I want to switch between List, Board, and Calendar views without server calls, so that I can quickly choose the visualization that suits my workflow.

#### Acceptance Criteria

1. WHEN the user clicks the List view button, THE View_Renderer SHALL render the Task_Store data as a tabular list without making a server request.
2. WHEN the user clicks the Board view button, THE View_Renderer SHALL render the Task_Store data as a Kanban board grouped by status without making a server request.
3. WHEN the user clicks the Calendar view button, THE View_Renderer SHALL render the Task_Store data as a calendar layout organized by due_date without making a server request.
4. WHEN the user switches views, THE View_Renderer SHALL preserve the currently active filters, scope, and sort order.
5. WHEN the user switches views, THE View_Renderer SHALL update the URL query parameter to reflect the active view without triggering a page reload.
6. WHEN a view switch completes, THE View_Renderer SHALL update the active visual state of the view switcher buttons so that only the current view button appears selected.
7. WHILE a view is being rendered, THE View_Renderer SHALL display a brief skeleton placeholder matching the target view layout (list rows for List, kanban columns for Board, or calendar grid for Calendar).

### Requirement 3: Client-Side Scope Toggle

**User Story:** As an officer, I want to toggle between "My Tasks" and "All Tasks" instantly, so that I can focus on my own work or see the full team workload.

#### Acceptance Criteria

1. WHEN the user selects "My Tasks", THE Filter_Engine SHALL filter the Task_Store to show only tasks where the Current_User is in assigned_officers or is created_by.
2. WHEN the user selects "All Tasks", THE Filter_Engine SHALL show all tasks in the Task_Store without scope filtering.
3. WHEN the scope changes, THE View_Renderer SHALL re-render the active view with the filtered dataset within 50 milliseconds for datasets of 500 tasks or fewer, without making a server request.
4. WHEN the scope changes, THE Scope_Toggle SHALL update the URL query parameter `scope` to reflect the active scope (value `my_tasks` or `all`) using the History API pushState without triggering a page reload.
5. THE Task_Store SHALL remember the last active scope selection for the duration of the browser session, defaulting to `my_tasks` when no prior selection exists.
6. WHEN the scope changes, THE Scope_Toggle SHALL visually indicate the currently active scope by applying an active style to the selected option and removing it from the previously selected option.

### Requirement 4: Client-Side Filtering

**User Story:** As an officer, I want to filter tasks by status, priority, category, officer, and search text instantly, so that I can find relevant tasks without waiting for server responses.

#### Acceptance Criteria

1. WHEN the user selects a status filter, THE Filter_Engine SHALL show only tasks matching the selected status value and hide all non-matching tasks from the active view.
2. WHEN the user selects a priority filter, THE Filter_Engine SHALL show only tasks matching the selected priority value and hide all non-matching tasks from the active view.
3. WHEN the user selects a category filter, THE Filter_Engine SHALL show only tasks matching the selected category value and hide all non-matching tasks from the active view.
4. WHEN the user selects one or more officer filters, THE Filter_Engine SHALL show only tasks where at least one selected officer is in assigned_officers and hide all non-matching tasks from the active view.
5. WHEN the user types a search query of 1 or more characters (maximum 200 characters), THE Filter_Engine SHALL show only tasks where the title, task_number, or description contains the query text (case-insensitive substring match).
6. WHEN multiple filters are active simultaneously, THE Filter_Engine SHALL apply all filters with AND logic, displaying only tasks that satisfy every active filter condition.
7. WHEN any filter changes, THE View_Renderer SHALL re-render the active view (list table, board columns, or calendar grid) within 50 milliseconds for datasets of 500 tasks or fewer.
8. THE Filter_Engine SHALL update URL query parameters to reflect active filters without triggering a page reload, using the parameter names: `status`, `priority`, `category`, `officer`, and `q`.
9. IF no tasks match the current combination of active filters, THEN THE Filter_Engine SHALL display an empty-state message indicating that no tasks match the applied filters and show the count of total tasks available before filtering.
10. WHEN a filter is reset to its default "All" value, THE Filter_Engine SHALL remove that filter's query parameter from the URL and include all tasks for that dimension in the results.

### Requirement 5: Client-Side Sorting

**User Story:** As an officer, I want to sort tasks by various fields instantly, so that I can organize my task view by priority, due date, or other criteria.

#### Acceptance Criteria

1. WHEN the user clicks a sortable column header, THE Filter_Engine SHALL reorder the currently displayed task rows in the browser by the selected field without making a server request.
2. THE Filter_Engine SHALL support client-side sorting by the following fields: task_number (numeric), title (alphabetical case-insensitive), priority (logical rank), status (workflow rank), due_date (chronological), and progress (numeric 0-100).
3. WHEN the user clicks the same sortable column header consecutively, THE Filter_Engine SHALL cycle through three states in order: ascending, descending, and original server order.
4. WHEN sorting by priority, THE Filter_Engine SHALL use the logical rank order: urgent (1), high (2), medium (3), low (4).
5. WHEN sorting by status, THE Filter_Engine SHALL use the workflow rank order: not_started (1), processing (2), to_advisers (3), accounting (4), oca (5), osas (6), ppss (7), supply (8), completed (9), overdue (10).
6. WHEN the user selects a sort option from the sort dropdown control, THE Filter_Engine SHALL update the URL query parameter `sort` to reflect the selected value without triggering a page reload.
7. IF a task has no due_date value, THEN THE Filter_Engine SHALL sort that task after all tasks with a due_date when sorting in ascending order, and before all tasks with a due_date when sorting in descending order.
8. THE Filter_Engine SHALL default to descending created_at order (newest first) when no sort parameter is present in the URL.

### Requirement 6: CRUD Operations with Local Store Patching

**User Story:** As an officer, I want task create, update, and delete operations to update the local view immediately after the server confirms success, so that the task list stays current without a full page refresh.

#### Acceptance Criteria

1. WHEN the server confirms a successful task creation by returning the created task object data, THE CRUD_Service SHALL add the new task object to the Task_Store and THE View_Renderer SHALL re-render the active view to reflect the addition.
2. WHEN the server confirms a successful task update (including status moves and progress updates) by returning the updated task object data, THE CRUD_Service SHALL update the corresponding task object in the Task_Store and THE View_Renderer SHALL re-render the active view to reflect the changes.
3. WHEN the server confirms a successful task deletion, THE CRUD_Service SHALL remove the task object from the Task_Store and THE View_Renderer SHALL re-render the active view to reflect the removal.
4. IF a CRUD operation fails (server returns an error or network request fails), THEN THE CRUD_Service SHALL display an error notification to the user that remains visible for at least 5 seconds or until manually dismissed, and THE Task_Store SHALL remain unchanged.
5. WHILE a CRUD operation is in progress for an existing task (update or delete), THE View_Renderer SHALL display a loading indicator on the affected task element.
6. WHILE a task creation operation is in progress, THE View_Renderer SHALL display a loading indicator on the submit button or form that initiated the creation.

### Requirement 7: URL State Synchronization

**User Story:** As an officer, I want the URL to reflect my current view, scope, filters, and sort, so that I can bookmark or share specific task views and use browser back/forward navigation.

#### Acceptance Criteria

1. WHEN the Tasks tab page loads, THE Task_Store SHALL read the view (list, board, or calendar from the `view` URL parameter), scope (query parameter `scope` with values `my_tasks` or `all`, defaulting to `my_tasks`), filters (query parameters `status`, `category`, `priority`, `officer`, `q`), and sort (query parameter `sort`, defaulting to `-created_at`) from the current URL and apply them to the rendered view.
2. WHEN the user changes any view, scope, filter, or sort setting, THE Task_Store SHALL update the URL query parameters using the History API pushState within 500 milliseconds without triggering a page reload, encoding all active parameters such that the resulting URL reproduces the current view state when loaded independently.
3. WHEN the user navigates using browser back or forward buttons (popstate event), THE Task_Store SHALL restore the view state (view, scope, filters, sort) from the URL present in the history entry and re-render the task view to match the restored state within 1 second.
4. WHEN the user loads the Tasks tab from a URL containing query parameters, THE Filter_Engine SHALL apply the encoded filters and THE View_Renderer SHALL render the corresponding view with all filter controls reflecting the active parameter values.
5. IF a URL contains an unrecognized query parameter name or an invalid value for a recognized parameter (e.g., `scope=invalid` or `sort=unknown_field`), THEN THE Task_Store SHALL ignore the invalid parameter and apply the default value for that parameter without displaying an error.

### Requirement 8: Role-Based Data Access

**User Story:** As a system administrator, I want the data API to enforce role-based access, so that officers only receive task data they are authorized to view.

#### Acceptance Criteria

1. WHILE the Current_User has task override privileges (super_admin, org_admin, or president role), THE Data_API SHALL return all non-archived tasks belonging to the Current_User's active organization.
2. WHILE the Current_User is an executive or committee_head, THE Data_API SHALL return only non-archived tasks where the Current_User is in assigned_officers or is created_by, scoped to the Current_User's organization.
3. IF the Current_User's organization does not match the requested organization, THEN THE Data_API SHALL reject the request with an HTTP 403 response and return zero task records.
4. IF the Current_User is not authenticated, THEN THE Data_API SHALL return an HTTP 401 response and include no task data in the response body.
5. WHILE the Current_User is a super_admin with no active organization context, THE Data_API SHALL return all non-archived tasks across all organizations.

### Requirement 9: Performance and Data Freshness

**User Story:** As an officer, I want the task data to stay fresh during my session without manual refresh, so that I see changes made by other team members.

#### Acceptance Criteria

1. THE Data_API SHALL return the full dataset in under 2 seconds for organizations with up to 1000 tasks, measured from request receipt to response completion.
2. THE Task_Store SHALL provide a manual refresh button that re-fetches all data from the Data_API and replaces the local store.
3. WHEN the user triggers a manual refresh, THE View_Renderer SHALL display a loading indicator and re-render the view on completion.
4. THE Data_API SHALL execute no more than 5 database queries when serving the task list endpoint for a single organization, using select_related and prefetch_related to batch relationship loading.
5. THE Task_Store SHALL store data only in JavaScript memory and SHALL NOT persist data to localStorage or sessionStorage to avoid serving stale content across sessions.

# SYSTEM_GUIDE.md
# CSG Task Management System - Proponent & Administrator Guide

## 1. System Overview
The CSG (Central Student Government) Task Management System is a centralized platform designed to streamline task assignment, monitoring, and reporting across various student organizations.

**Primary Workflow:**
1. Users log in with their credentials.
2. They are directed to the **Dashboard** which provides an overview of active, completed, and pending tasks.
3. Users can navigate to the **Tasks** module (viewable as a List, Kanban Board, or Calendar) to create, assign, or update tasks.
4. Progress is tracked in real-time, and **Reports** can be generated and exported in PDF or Excel formats.
5. Administrators use the **Officers** and **Settings** modules to manage user access and organizational structures.

**Major Modules:**
- **Dashboard**: High-level statistical overview of productivity.
- **Tasks**: Core module for creating, tracking, and managing work items.
- **Monitoring & Reports**: Tracks system activity and generates downloadable task reports.
- **Officers & Positions**: Manages user accounts and their titles within the organization.
- **Organizations**: (Super Admin only) Manages multiple tenant organizations within the system.
- **Notifications**: In-app alerts for assignments, nudges, and updates.

---

## 2. User Roles & RBAC

The system employs a strict Role-Based Access Control (RBAC) mechanism.

| Feature/Action | Super Admin | Org Admin | President | Elected Officer | Committee Member |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **View Dashboard & Reports** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Create Tasks** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Edit/Update Own/Assigned Tasks**| ✓ | ✓ | ✓ | ✓ | ✓ |
| **Override/Edit ANY Task** | ✓ | ✓ | ✓ | — | — |
| **Manage Officers & Positions** | ✓ (All) | ✓ (Own Org) | ✓ (Own Org)| — | — |
| **Manage Organizations** | ✓ | — | — | — | — |
| **Verify Task Completion/Deletion**| — | ✓ | — | — | — |

**Role Details:**
- **Super Admin:** System-wide administrator. Can switch between different organizations' workspaces, manage all users, and approve/reject new organizations. Cannot bypass the Org Admin password requirement for task deletion/completion.
- **Org Admin:** The primary manager for a specific organization. Can manage their officers and positions. **Crucially, only the Org Admin's password can be used to authorize sensitive task actions (edit, complete, delete) within their organization.**
- **President:** High-level organizational role. Can manage officers and has override privileges to edit any task, but cannot authorize sensitive task deletions.
- **Elected Officer / Committee Member:** Standard users. Can view data, create tasks, and update progress only on tasks they created or are explicitly assigned to.

---

## 3. Authentication & Account Management

- **Login:** Users authenticate via the `/accounts/login/` page using their username and password.
- **Post-Login:** Successful authentication redirects users to the Dashboard scoped to their specific organization (or the system-wide dashboard for Super Admins).
- **Session Handling:** The system uses standard secure session cookies. Users can manually log out via the profile dropdown.
- **Forgot Password:** Users can click "Forgot Password" on the login screen to receive an email with a secure, time-sensitive reset link.
- **Account Management:** Users can update their profile picture and change their password via the **Profile** and **Change Password** modals.
- **Admin Reset:** If a user loses access, an Org Admin or Super Admin can edit the officer's profile or recreate the account. Newly created officers default to a standard password (e.g., `csg202627`) which they should change immediately upon login.

---

## 4. Password / System Reset Procedures

### User-Initiated Password Reset
1. Go to the Login page and click **Forgot Password?**
2. Enter the registered email address.
3. Check the email inbox for the reset link.
4. Click the link and enter a new password.

### Administrator-Initiated Account Reset
If a user is completely locked out and cannot use the email reset:
1. Log in as an **Org Admin** or **Super Admin**.
2. Navigate to **Officers**.
3. Select the user and click **Edit**.
4. (To fully reset, an admin may need to delete and recreate the officer account, setting a temporary password like `csg202627`. The user must change this immediately).

### Removing a Profile Picture
1. Navigate to **Officers** (as an Admin) or **Profile** (as the user).
2. Click **Edit**.
3. Select the option to **Remove Photo**. This instantly clears the avatar and reverts to initials.

*(Note: Database or system-wide configuration resets require Developer intervention.)*

---

## 5. Common Operations

### Managing Users (Officers)
1. Go to **Officers** in the sidebar.
2. Click **Add Officer** to create a new user. Assign them a Role and a Position.
3. Use the **Edit** (pencil) or **Delete** (trash) icons next to an existing officer to modify their access. 

### Managing Positions
1. Go to **Positions** under the Management section in the sidebar.
2. Click **Add Position** to define a new title (e.g., "Secretary General").
3. These titles can then be assigned to Officers to clarify their exact duties beyond their system role.

### Creating and Managing Tasks
1. Go to **Tasks**.
2. Click **New Task**. Fill in the title, description, priority, category, and assign specific officers.
3. **Updating Progress:** Assigned officers can click the task and update the slider or move it across the Kanban board.
4. **Completing/Deleting:** When attempting to mark a task as Complete or Delete it, the system will prompt for a password. **You must enter the Org Admin's password to proceed.**

---

## 6. Important Rules & Restrictions

- **Strict Org Admin Authorization:** Deleting tasks, completing tasks, or bulk-modifying tasks strictly requires the **Org Admin's password**. Even a Super Admin cannot bypass this requirement using their own password.
- **Task Archiving vs. Deletion:** Tasks are typically soft-deleted (archived) to preserve history. Permanent deletion requires admin authorization and removes the task from all views.
- **Cache Invalidation:** The system caches officer lists and task data for speed. When you add a new officer or edit a task, the system automatically clears the cache so changes reflect instantly.
- **Action Confirmation:** Deleting an officer account requires the administrator to manually type the word `DELETE` to prevent accidental data loss. Deleting an officer also removes their assigned tasks and notifications.
- **Dynamic Theming:** The system's color scheme (Dark/Light mode and Organization colors) automatically adapts based on the active Organization's settings.

---

## 7. Troubleshooting

| Issue | Recommended Action | When to contact Developer |
| :--- | :--- | :--- |
| **Cannot log in / Forgot Password** | Use the "Forgot Password" link on the login page. | If no email is received after 15 minutes. |
| **Access Denied to a page** | Ensure you have the correct role (e.g., trying to access Positions requires Admin privileges). | If an Org Admin is denied access to their own org's settings. |
| **Cannot Complete/Delete a Task** | The system strictly requires the **Org Admin** password. Ensure you are typing the correct password for the Org Admin account. | If the Org Admin password is forgotten and the account is locked. |
| **New Officer not appearing** | Refresh the page. The system caches data for 60 seconds, though it usually auto-clears on creation. | If the officer is still missing after 5 minutes. |
| **Badge cutoff on mobile** | Fixed automatically, ensure your mobile browser cache is cleared (`Clear History/Data`). | If layout issues persist across multiple devices. |

---

## 8. Data & Security Considerations

- **Data Isolation:** Officers can only see tasks and users within their own Organization. Only the Super Admin has cross-organization visibility.
- **Admin Credentials:** The Org Admin password acts as the master key for all destructive actions (deletions/completions) in an organization. **Never share the Org Admin password.**
- **Audit Logging:** Destructive actions (deleting users, deleting tasks, removing photos) are logged in the system's audit trail (`log_activity`).
- **Session Security:** Always log out when using a shared device.

---

## 9. Developer/System Administrator Notes

The following operations are not exposed via the web interface and require backend/developer access:
- **Direct Database Modifications:** Manual SQL queries or Django Admin (`/admin/`) access.
- **Server Deployment & Environment Variables:** Modifying `settings.py`, database credentials (`.env`), or Redis cache configurations.
- **Recovering Locked Super Admin:** If the sole Super Admin forgets their password and cannot use email recovery, a developer must use the terminal (`python manage.py changepassword <username>`) to restore access.
- **System-wide Theme Customization:** Adding new CSS themes beyond the predefined `THEME_CHOICES` in `organizations/models.py`.

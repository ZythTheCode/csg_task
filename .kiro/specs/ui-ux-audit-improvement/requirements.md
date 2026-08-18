# Requirements Document

## Introduction

This feature addresses a comprehensive UI/UX audit of the CSG Task Management and Monitoring System. The audit identified inconsistencies in dark mode styling, layout shift problems, mobile responsiveness gaps, browser-native alert() usage, excessive inline styles, and accessibility shortcomings. This requirements document defines the improvements needed to bring the frontend to a polished, consistent, and accessible state while preserving all existing functionality including organization theming, sidebar navigation, chart rendering, and AJAX patterns.

## Glossary

- **Application**: The CSG Task Management and Monitoring System Django web application
- **Dark_Mode_Engine**: The subsystem responsible for applying dark mode styles when `data-mode="dark"` is set on the HTML element
- **Theme_System**: The CSS custom property-based theming system that applies organization-specific colors via the `data-theme` attribute
- **Design_Token_System**: The set of CSS custom properties defined in `:root` that standardize spacing, colors, radii, shadows, and typography values
- **Layout_Renderer**: The browser rendering engine responsible for computing element positions and sizes during page load
- **Responsive_Layout_System**: The CSS media queries and flexible layouts that adapt the interface to different viewport widths
- **Alert_System**: The existing modal and toast notification infrastructure used to display messages to users
- **Style_Engine**: The CSS class-based styling system that applies visual presentation to HTML elements
- **Table_Component**: The task list table element with sorting, pagination, and action buttons
- **Form_Component**: Input elements including text fields, selects, date pickers, and search bars used in filters and task creation
- **Modal_Component**: Bootstrap 5 modal dialogs used for task details, confirmations, image cropping, and nudge actions
- **Typography_System**: The font family, size, weight, and spacing rules applied to text elements
- **Spacing_System**: The 8-point spacing scale defined as design tokens for consistent padding, margin, and gap values
- **Accessibility_Layer**: ARIA attributes, focus management, color contrast, and semantic HTML that enable assistive technology usage
- **CLS**: Cumulative Layout Shift — a Core Web Vital metric measuring unexpected visual movement during page load
- **Viewport**: The visible area of the browser window, measured in width (e.g., 320px for small mobile, 768px for tablet)

## Requirements

### Requirement 1: Dark Mode Consistency

**User Story:** As a user who prefers dark mode, I want all UI elements to render correctly in dark mode without visual artifacts, so that I can use the application comfortably in low-light environments.

#### Acceptance Criteria

1. WHILE dark mode is active, THE Dark_Mode_Engine SHALL apply dark background colors to all card, input, dropdown, and container elements by overriding CSS custom properties (e.g., `--pink-50`, `--pink-100`) on the `[data-mode="dark"]` selector, without using `!important` overrides on inline style attribute selectors
2. WHILE dark mode is active, THE Dark_Mode_Engine SHALL ensure all text elements maintain a minimum contrast ratio of 4.5:1 against their background color, as defined by WCAG 2.1 AA success criterion 1.4.3
3. WHILE dark mode is active, THE Dark_Mode_Engine SHALL remap Bootstrap utility classes `.bg-white`, `.bg-light`, `.bg-body`, `.text-dark`, and `.border-light` to their dark-surface equivalents such that background lightness does not exceed 25% HSL lightness and text lightness is at minimum 75% HSL lightness
4. WHILE dark mode is active, THE Dark_Mode_Engine SHALL render Chart.js chart backgrounds with a surface color matching the card container background, gridlines at no more than 15% opacity against the surface, and labels and tooltip text maintaining the 4.5:1 minimum contrast ratio defined in criterion 2
5. WHILE dark mode is active, THE Dark_Mode_Engine SHALL apply dark mode styles exclusively through CSS custom property overrides on the `[data-mode="dark"]` selector rather than targeting inline `style` attributes directly
6. WHILE dark mode is active AND an organization theme is applied via `[data-theme]` attribute, THE Dark_Mode_Engine SHALL preserve the organization's `--primary`, `--primary-light`, and `--primary-dark` custom property values unchanged while adapting all non-accent surface and background custom properties to dark variants with lightness not exceeding 25% HSL
7. WHEN the user toggles dark mode, THE Dark_Mode_Engine SHALL apply all style changes within 300 milliseconds without requiring a page reload
8. WHEN an AJAX fragment is loaded into the page while dark mode is active, THE Dark_Mode_Engine SHALL apply dark mode styles to the newly inserted fragment content without additional user action or visible flash of light-mode styling
9. IF the `[data-mode="dark"]` attribute is set on the document root before initial page render, THEN THE Dark_Mode_Engine SHALL render the page in dark mode on first paint without a visible flash of light-mode styling

### Requirement 2: Layout Shift Prevention

**User Story:** As a user loading the application, I want the page layout to remain stable during load, so that I do not experience jarring visual movement that disrupts my interaction.

#### Acceptance Criteria

1. THE Layout_Renderer SHALL reserve explicit dimensions (minimum height of 220px) for all chart containers before chart data loads, preventing content reflow when charts render
2. WHEN task detail modal content loads asynchronously, THE Modal_Component SHALL maintain a minimum height of 200px on the modal body during the loading state, preventing the modal from resizing when content appears
3. THE Layout_Renderer SHALL apply the sidebar collapsed or expanded state before the first meaningful paint by reading the `csg_sidebar_minimized` localStorage key in a synchronous inline script placed before the main content renders
4. WHEN toast notifications appear, THE Alert_System SHALL position them in a fixed-position overlay (using CSS `position: fixed`) with a z-index above page content, so that they do not displace or reflow page content
5. THE Layout_Renderer SHALL ensure all images and media elements have explicit width and height attributes or aspect-ratio CSS to prevent reflow on load
6. WHEN chart data fails to load or is loading, THE Layout_Renderer SHALL maintain the reserved chart container dimensions so that the layout remains stable regardless of load outcome

### Requirement 3: Mobile Responsiveness

**User Story:** As a user accessing the application on a mobile device, I want the interface to be fully usable on screens as narrow as 320px, so that I can manage tasks from my phone.

#### Acceptance Criteria

1. WHILE the viewport width is 320px or greater, THE Responsive_Layout_System SHALL render all filter bar controls without horizontal overflow, using vertical stacking when viewport width is below 576px or a horizontally scrollable container when viewport width is between 576px and 767px
2. WHILE the viewport width is less than 768px, THE Responsive_Layout_System SHALL render select elements in the filter bar at a minimum width that displays at least 12 characters of option text without truncation
3. WHILE the viewport width is less than 768px, THE Table_Component SHALL render action buttons with a minimum tap target size of 44x44 CSS pixels
4. WHILE the viewport width is less than 768px, THE Responsive_Layout_System SHALL render all text content at a computed font size no smaller than 12px and use relative units (rem or em) so that no single line of text causes the page to scroll horizontally
5. WHILE the viewport width is less than 768px, THE Modal_Component SHALL occupy 100% of the viewport width minus 16px of horizontal padding (8px per side), limit its height to 90vh, and scroll content internally within the modal body rather than exceeding the viewport height
6. WHILE the viewport width is less than 768px, THE Responsive_Layout_System SHALL replace inline pixel-based padding and font sizes with responsive relative units, ensuring no padding value exceeds 16px and no font size falls below 12px at the 320px viewport width
7. WHILE the viewport width is less than 576px, THE Responsive_Layout_System SHALL stack all filter bar controls (search input, category select, status select, priority select, officer multi-select, and action buttons) into a single vertical column at full available width

### Requirement 4: Replace Browser-Native alert() Calls

**User Story:** As a user interacting with the application, I want all feedback messages to appear in styled modal dialogs or toast notifications consistent with the application design, so that the experience feels cohesive and professional.

#### Acceptance Criteria

1. WHEN a password verification error occurs in the task edit flow, THE Alert_System SHALL display the error message using the existing toast notification component instead of a browser-native `alert()` dialog
2. WHEN a mark-complete operation fails, THE Alert_System SHALL display the failure message using the existing toast notification component instead of a browser-native `alert()` dialog
3. WHEN a task detail API request fails, THE Alert_System SHALL display the error message using the existing toast notification component instead of a browser-native `alert()` dialog
4. WHEN a nudge officer validation fails due to no officers selected, THE Alert_System SHALL display the validation message using the existing toast notification component instead of a browser-native `alert()` dialog
5. THE Application SHALL contain zero calls to the browser-native `alert()` function across all `.html` template files and all `.js` static JavaScript files
6. WHEN displaying error or validation messages via toast, THE Alert_System SHALL render the toast using the Bootstrap `alert-danger` class, include a visible close button for manual dismissal, and auto-dismiss the toast after no more than 5 seconds
7. THE Application SHALL define the `showToastNotification()` function in a globally loaded template or static JavaScript file so that it is available on every page without requiring a specific modal or partial to be present

### Requirement 5: Inline Style Consolidation

**User Story:** As a developer maintaining the application, I want repeated inline styles extracted into reusable CSS utility classes, so that the codebase is maintainable and styling is consistent.

#### Acceptance Criteria

1. THE Style_Engine SHALL define reusable CSS classes in the project stylesheet for the filter select pattern (font-size: 12.5px, border-radius: 10px, width: auto, min-width between 110px and 150px, max-width between 140px and 150px, padding: 6px 28px 6px 10px, border-color using the --slate-200 token) currently repeated via inline styles across task list, board, and calendar templates
2. THE Style_Engine SHALL define reusable CSS classes in the project stylesheet for the scope switcher pattern (font-weight: 700, font-size: 12px–12.5px, border-radius: 20px, padding: 4px 14px) and view switcher pattern (font-size: 12px, padding: 4px 14px, border-radius: 20px) currently duplicated with inline styles across dashboard and task list templates
3. THE Style_Engine SHALL define reusable CSS classes in the project stylesheet for badge styling patterns (font-size: 10.5px, font-weight: 600, padding: 4px 8px, border-radius: 12px) that are currently applied via inline styles on officer assignment badges and overflow count badges
4. THE Style_Engine SHALL define reusable CSS classes in the project stylesheet for button variant patterns (font-size: 12px, padding: 6px 14px–16px, border-radius: 10px–20px, white-space: nowrap) that are currently styled with inline styles on filter Apply buttons, Reset links, and New Task action buttons
5. WHEN inline styles are extracted into classes, THE Style_Engine SHALL replace inline style attributes in templates with the corresponding CSS class references such that no inline style attribute remains for any pattern covered by criteria 1–4
6. WHEN inline styles are replaced with CSS classes, THE Style_Engine SHALL produce rendered output where each affected element retains the same computed font-size, padding, border-radius, min-width, max-width, and border-color values as the original inline-styled rendering, verified by comparing computed styles before and after the change
7. THE Style_Engine SHALL use existing design tokens (--space-1 through --space-8 spacing scale, --radius-xs through --radius-pill radius scale, and color variables such as --slate-200) in the new utility classes rather than hardcoded pixel values, except where no existing token matches the required value within 2px tolerance

### Requirement 6: Table Component Improvements

**User Story:** As a user viewing the task list on a mobile device or in dark mode, I want the table to be readable and interactive, so that I can efficiently manage my tasks in any context.

#### Acceptance Criteria

1. WHILE the viewport width is less than 768px, THE Table_Component SHALL reduce table header padding to no more than 10px vertical and 8px horizontal, and cell padding to no more than 8px vertical and 8px horizontal, while maintaining a minimum tap target size of 44x44 CSS pixels for all interactive elements (action buttons, sort headers, and links) within the table
2. WHILE dark mode is active (indicated by the `data-mode="dark"` or `data-theme="dark"` attribute on a parent element), THE Table_Component SHALL apply dark-themed colors to all table elements — including the container background, thead headers, tbody rows, even/odd striped rows, row hover states, cell text, cell borders, and in-cell links — such that no element displays light-mode default colors
3. WHEN the user performs a table sort action by clicking a sortable column header, THE Table_Component SHALL update only the sort indicator icon elements within that table (replacing the icon SVG content inline) without calling a full icon library reinitialization across the page
4. WHILE the viewport width is less than 768px AND the table content width exceeds the visible container width, THE Table_Component SHALL display a visual scroll affordance (shadow or fade overlay) on the edge toward which additional content is available, and SHALL hide that affordance on an edge when the user has scrolled fully to that edge
5. WHEN the user performs a table sort action by clicking a sortable column header, THE Table_Component SHALL display a directional indicator (upward for ascending, downward for descending) on the active column and a neutral indicator on all other sortable columns, cycling through ascending, descending, and original order on repeated clicks of the same column

### Requirement 7: Form Styling Consistency

**User Story:** As a user filling out forms and filters, I want all input elements to have a consistent visual appearance, so that the interface feels cohesive and predictable.

#### Acceptance Criteria

1. THE Form_Component SHALL apply a single border-radius design token (one of `--radius-xs`, `--radius-sm`, or `--radius-md`) to all text inputs, select elements, and search bars, with no inline or hardcoded border-radius values overriding the token; for input-group compositions, the token value SHALL apply to the outer corners of the first and last child elements only
2. THE Form_Component SHALL apply a uniform font-size of no less than 13px and no greater than 14px, specified via a design token or a single shared CSS custom property, to all filter controls, form inputs, and search fields
3. WHILE dark mode is active, THE Form_Component SHALL render input borders, backgrounds, placeholder text, and focus rings using the dark-mode color tokens defined in the design token system such that text-to-background contrast meets a minimum ratio of 4.5:1 and placeholder-to-background contrast meets a minimum ratio of 3:1
4. THE Form_Component SHALL associate every filter control and form input with a programmatically determinable label via an HTML `<label>` element with a matching `for` attribute or an `aria-label` attribute, so that no input relies solely on placeholder text for identification
5. WHEN a form input receives focus, THE Form_Component SHALL display a focus ring using the `--focus-ring` design token (`0 0 0 3px rgba(255, 79, 163, 0.35)`) that produces a contrast ratio of at least 3:1 against the adjacent background in both light and dark mode

### Requirement 8: Modal Behavior on Small Screens

**User Story:** As a mobile user interacting with modals, I want modal content to be fully visible and scrollable without overflowing the screen, so that I can complete modal-based workflows on any device.

#### Acceptance Criteria

1. WHILE the viewport width is less than 576px, THE Modal_Component SHALL render modal dialogs at full viewport width minus horizontal margin (minimum 8px on each side), resulting in a maximum dialog width of calc(100vw - 16px)
2. WHILE the viewport width is less than 576px, THE Modal_Component SHALL constrain the overall modal content to a maximum height of 90vh, with the modal body scrollable via overflow-y auto and limited to the remaining height after subtracting the fixed-height header and footer (no greater than calc(90vh - 120px))
3. WHEN a nested modal opens over an existing modal (e.g., nudge modal over task detail modal), THE Modal_Component SHALL render the nested modal at a higher z-index than the parent modal (nested modal z-index greater than parent modal z-index by at least 10) and display a separate backdrop between the two modals so that the nested modal is fully visible and receives all user interaction
4. WHILE the viewport width is less than 576px, THE Modal_Component SHALL size interactive elements within the modal (buttons, inputs) with a minimum tap target of 44x44 CSS pixels
5. WHILE a modal is open and the viewport width is less than 576px, THE Modal_Component SHALL prevent scrolling of the page content behind the modal (body scroll lock)
6. WHEN a nested modal is dismissed, THE Modal_Component SHALL restore the parent modal to its prior visible and interactive state without requiring the user to reopen it

### Requirement 9: Typography Standardization

**User Story:** As a user reading content in the application, I want consistent typography that establishes clear visual hierarchy, so that I can quickly scan and understand the interface.

#### Acceptance Criteria

1. THE Typography_System SHALL define a type scale with exactly 6 distinct font sizes mapped to CSS custom properties (e.g., `--font-size-xs` through `--font-size-xl` and `--font-size-display`), where each step is between 1.125x and 1.333x larger than the previous step, and all values use rem units
2. THE Typography_System SHALL provide utility classes for each type scale step, and no component or template shall apply font sizes via inline styles or hardcoded px values outside of these utility classes
3. THE Typography_System SHALL apply consistent heading hierarchy where page titles use the largest heading size in the scale, card headers use the next step down, and section labels use a further step down, with each level using a single defined font-weight value (one of 600, 700, or 800)
4. THE Typography_System SHALL apply a uniform letter-spacing value to all headings at the same hierarchy level, where display/page-title headings use a negative letter-spacing between -0.5px and -0.2px, and uppercase labels use a positive letter-spacing between 0.4px and 1.2px
5. THE Typography_System SHALL use rem units in all type scale custom properties and utility classes so that text scales proportionally when the user changes their browser's base font size
6. WHILE dark mode is active, THE Typography_System SHALL maintain identical font sizes, font weights, letter-spacing, and line-height values as light mode, changing only color values
7. THE Typography_System SHALL define no more than 3 distinct line-height values (one for headings, one for body text, and one for compact UI labels) applied consistently through the utility classes

### Requirement 10: Spacing Consistency

**User Story:** As a user navigating the application, I want consistent spacing between elements, so that the interface feels orderly and the design appears intentional.

#### Acceptance Criteria

1. THE Spacing_System SHALL define utility classes that map to the existing 8-point spacing scale (`--space-1` through `--space-8`) for padding and margin
2. THE Style_Engine SHALL apply spacing utility classes or design token variables for gap values in flex and grid containers, replacing arbitrary pixel values with the nearest token value by rounding to the closest token in the scale (e.g., 2px rounds to `--space-1` 4px, 6px rounds to `--space-2` 8px, 10px rounds to `--space-3` 12px, 18px rounds to `--space-4` 16px)
3. THE Style_Engine SHALL apply padding inside card components (elements using the `glass-card` class) using spacing tokens, with a minimum of `--space-3` (12px) and a maximum of `--space-5` (24px), and each distinct card type SHALL use a single consistent token value across all instances
4. THE Style_Engine SHALL apply a consistent margin of `--space-3` (12px) to `--space-5` (24px) between consecutive page sections (top-level content blocks within the main content area), using the same token value for all same-level sibling sections on a given page
5. WHEN spacing tokens are applied, THE Style_Engine SHALL ensure that no inline `style` attributes contain arbitrary pixel values (values not matching a defined token) for `padding`, `margin`, or `gap` properties, and the computed spacing between adjacent interactive elements is no less than `--space-1` (4px)

### Requirement 11: Accessibility Improvements

**User Story:** As a user relying on assistive technology or keyboard navigation, I want the application to provide appropriate semantic markup and interaction cues, so that I can use the application effectively.

#### Acceptance Criteria

1. WHEN a user clicks a `.sortable-header` element, THE Accessibility_Layer SHALL set the `aria-sort` attribute on that header to `"ascending"` or `"descending"` matching the active sort direction, and SHALL set `aria-sort="none"` on all other sortable headers in the same table
2. THE Accessibility_Layer SHALL ensure all interactive elements (buttons, links, toggles) display a visible focus indicator in both light and dark mode using the `--focus-ring` design token with a minimum 3px outline offset that meets WCAG 2.1 Level AA non-text contrast ratio (3:1 against adjacent colors)
3. THE Accessibility_Layer SHALL provide a visible `<label>` element or an `aria-label` attribute for every filter `<select>` control, including those that currently rely solely on a placeholder `<option>` (e.g., the Officer filter)
4. WHEN a toast notification appears, THE Accessibility_Layer SHALL mark the notification container with `role="alert"` and `aria-live="assertive"` so screen readers announce it immediately
5. THE Accessibility_Layer SHALL ensure all icon-only buttons (including dark mode toggle, notifications bell, mobile menu toggle, and logout link) include an `aria-label` attribute describing the button's action
6. THE Accessibility_Layer SHALL ensure each sidebar toggle button (`sidebar-expand-btn`, `sidebar-collapse-btn`, and the mobile menu toggle) has an `aria-expanded` attribute set to `"true"` when the sidebar is open/expanded and `"false"` when it is closed/minimized
7. WHEN a modal opens, THE Accessibility_Layer SHALL trap keyboard focus within the modal until it is closed
8. WHEN a modal is closed, THE Accessibility_Layer SHALL return keyboard focus to the element that triggered the modal opening

### Requirement 12: Preserve Existing Functionality

**User Story:** As a user of the application, I want all existing features to continue working after UI/UX improvements are applied, so that no functionality is lost during the visual refinement.

#### Acceptance Criteria

1. WHEN UI/UX improvements are applied, THE Application SHALL preserve all existing organization theming such that each of the 17 color themes defined in THEME_COLOR_MAP applies its corresponding CSS custom properties and gradient colors in both light mode and dark mode without visual breakage or fallback to default values
2. WHEN UI/UX improvements are applied, THE Application SHALL preserve the global confirmation modal system such that calling showConfirmModal() with title, message, icon, button text, button class, and optional password requirement displays the modal, accepts user input, and invokes the onConfirm callback for all destructive actions
3. WHEN UI/UX improvements are applied, THE Application SHALL preserve the sidebar collapse/expand behavior such that toggling writes the state to localStorage under the key csg_sidebar_minimized, page load restores the persisted state before first paint, and the collapse/expand CSS transition completes within 300 milliseconds
4. WHEN UI/UX improvements are applied, THE Application SHALL preserve all Chart.js chart rendering on the dashboard including the status doughnut, monthly bar, priority pie, officer horizontal bar, and weekly line charts with loading spinner overlay shown while data is fetched, correct data binding on API response, and proportional resizing when the viewport width changes
5. WHEN UI/UX improvements are applied, THE Application SHALL preserve the toast notification system such that Django messages with tags success, error, warning, and info render as dismissible alerts within the toast-container element and auto-dismiss after 4 seconds
6. WHEN UI/UX improvements are applied, THE Application SHALL preserve all AJAX-loaded content patterns including the task detail modal opening with full task data, comment submission via form post, and dynamic filter updates returning filtered results without full page reload
7. WHEN UI/UX improvements are applied, THE Application SHALL preserve the skeleton loading CSS system such that the skeleton.css file remains loaded, the skeleton-shimmer animation and skeleton-line class render the shimmer effect, and dark mode overrides apply via the data-mode attribute
8. IF a UI/UX improvement modifies any shared template or stylesheet, THEN THE Application SHALL maintain functional equivalence by ensuring that no existing JavaScript function referenced in base.html (including toggleSidebarMin, toggleUserDarkMode, showConfirmModal, updateTabFavicon, and loadCharts) throws an error or fails to execute

# Implementation Plan: UI/UX Audit Improvement

## Overview

This plan implements the comprehensive UI/UX audit improvements in dependency order: design tokens and utility classes first (CSS foundation), then template-level changes (HTML/JS), then integration and verification. Each task is scoped to specific files and references the requirements it satisfies.

## Tasks

- [x] 1. Extend design token system and add utility classes in style.css
  - [x] 1.1 Add typography scale tokens and utility classes
    - Add `--font-size-xs` through `--font-size-display` custom properties to `:root`
    - Add `--line-height-heading`, `--line-height-body`, `--line-height-compact`
    - Add `--font-weight-heading`, `--font-weight-subheading`, `--font-weight-label`
    - Add `--letter-spacing-title`, `--letter-spacing-uppercase`
    - Add `--input-font-size` and `--input-border-radius` form tokens
    - Create `.text-xs` through `.text-display` utility classes
    - Create `.heading-page`, `.heading-card`, `.heading-section`, `.label-uppercase` classes
    - File: `static/css/style.css`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

  - [x] 1.2 Add spacing utility classes
    - Create `.p-token-1` through `.p-token-5` with px, py, pt, pb, pl, pr variants
    - Create `.m-token-1` through `.m-token-5` with directional variants
    - Create `.gap-token-1` through `.gap-token-5` for flex/grid containers
    - File: `static/css/style.css`
    - _Requirements: 10.1, 10.2_

  - [x] 1.3 Add extracted component classes (inline style consolidation)
    - Create `.filter-select` class (font-size, border-radius, width, padding, border-color using tokens)
    - Create `.scope-switcher-btn` class
    - Create `.view-switcher-btn` class
    - Create `.badge-pill-sm` class
    - Create `.btn-action-compact` class
    - File: `static/css/style.css`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.7_

  - [x] 1.4 Add layout shift prevention CSS
    - Add `.chart-container { min-height: 220px; position: relative; }` rule
    - Add `.modal-body-loading { min-height: 200px; }` with flex centering
    - Ensure toast container uses `position: fixed` with appropriate z-index
    - File: `static/css/style.css`
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6_

  - [x] 1.5 Add mobile responsive CSS rules
    - Add `@media (max-width: 575.98px)` rules for `.filter-bar-controls` vertical stacking
    - Add `@media (min-width: 576px) and (max-width: 767.98px)` rules for horizontal scroll filter bar
    - Add mobile modal rules: full-width dialog, 90vh max-height, internal scroll
    - Add minimum tap target sizes (44px) for buttons, inputs, selects below 768px
    - Add `.table-scroll-wrapper` with shadow affordance and `.scrolled-end` state
    - Add table padding reduction for mobile (10px/8px)
    - File: `static/css/style.css`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 6.1, 6.4, 8.1, 8.2, 8.4_

  - [x] 1.6 Add dark mode gap-fill CSS rules
    - Add `[data-mode="dark"]` overrides for Bootstrap utility remapping (`.bg-white`, `.bg-light`, `.text-dark`, etc.)
    - Add dark mode rules for table elements (thead, tbody, striped rows, hover, borders, links)
    - Add dark mode rules for form inputs (borders, backgrounds, placeholder, focus ring)
    - Add dark mode chart container surface color
    - Ensure org theme `--primary` values preserved while surfaces adapt
    - File: `static/css/style.css`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 6.2, 7.3_

  - [x] 1.7 Add form styling consistency CSS
    - Apply `--input-border-radius` token to all `.form-control`, `.form-select` elements
    - Apply `--input-font-size` token uniformly to filter controls and form inputs
    - Add focus ring rule using `--focus-ring` token (`0 0 0 3px rgba(255, 79, 163, 0.35)`)
    - File: `static/css/style.css`
    - _Requirements: 7.1, 7.2, 7.5, 11.2_

- [x] 2. Checkpoint - Verify CSS foundation
  - Ensure all new CSS classes compile without syntax errors
  - Verify no existing styles are broken by loading the application
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Implement global JavaScript utilities in base.html
  - [x] 3.1 Add `showToastNotification()` global function
    - Define `window.showToastNotification(message, type, duration)` in a `<script>` block in `base.html`
    - Ensure it creates/finds `.toast-container`, creates alert element with correct class, auto-dismisses
    - Add `role="alert"` and `aria-live="assertive"` to toast container
    - Include close button with `aria-label="Close"`
    - File: `templates/base.html`
    - _Requirements: 4.6, 4.7, 11.4_

  - [x] 3.2 Add modal focus trap and body scroll lock
    - Add `show.bs.modal` listener to set `body.style.overflow = 'hidden'` on mobile (<576px)
    - Add `hidden.bs.modal` listener to restore overflow only when no modals remain open
    - Add `keydown` Tab trap logic: cycle focus within `.modal.show` between first/last focusable elements
    - Track trigger element and restore focus on modal close
    - File: `templates/base.html`
    - _Requirements: 8.5, 11.7, 11.8_

  - [x] 3.3 Add ARIA attributes to global interactive elements
    - Add `aria-label` to dark mode toggle button
    - Add `aria-label` to notifications bell icon button
    - Add `aria-label` to mobile menu toggle button
    - Add `aria-label` to logout link
    - Add `aria-expanded` to sidebar toggle buttons (`sidebar-expand-btn`, `sidebar-collapse-btn`)
    - File: `templates/base.html`
    - _Requirements: 11.5, 11.6_

- [x] 4. Refactor table-sort.js for inline SVG and accessibility
  - [x] 4.1 Replace lucide icon reinitialization with inline SVGs
    - Define `SVG_CHEVRON_UP`, `SVG_CHEVRON_DOWN`, `SVG_NEUTRAL` as constants
    - Replace `lucide.createIcons()` calls with direct `innerHTML` swap of SVG strings
    - File: `static/js/table-sort.js`
    - _Requirements: 6.3, 6.5_

  - [x] 4.2 Add `aria-sort` attribute management to sortable headers
    - On sort click, set `aria-sort="ascending"` or `"descending"` on active header
    - Set `aria-sort="none"` on all other sortable headers in the same table
    - File: `static/js/table-sort.js`
    - _Requirements: 11.1_

  - [x] 4.3 Add scroll affordance JavaScript for mobile table wrapper
    - Add scroll event listener to `.table-scroll-wrapper` elements
    - Toggle `.scrolled-end` class when scrolled fully to right edge
    - File: `static/js/table-sort.js` (or inline in `templates/tasks/list.html`)
    - _Requirements: 6.4_

- [ ] 5. Replace alert() calls and inline styles in task templates
  - [ ] 5.1 Refactor `templates/tasks/list.html`
    - Replace all `alert()` calls with `showToastNotification()` (password error, mark-complete fail)
    - Replace inline styles on filter selects with `.filter-select` class
    - Replace inline styles on view switcher buttons with `.view-switcher-btn` class
    - Replace inline styles on badge elements with `.badge-pill-sm` class
    - Replace inline styles on action buttons with `.btn-action-compact` class
    - Add `aria-sort="none"` to all sortable `<th>` elements
    - Add `aria-label` to filter select elements
    - Wrap table in `.table-scroll-wrapper` div for mobile scroll affordance
    - _Requirements: 4.1, 4.2, 4.5, 5.5, 5.6, 3.3, 7.4, 11.1, 11.3_

  - [ ] 5.2 Refactor `templates/tasks/detail.html`
    - Replace `alert()` call with `showToastNotification()` for API request failures
    - Add appropriate ARIA attributes
    - Replace any inline styles with utility classes
    - _Requirements: 4.3, 4.5_

  - [ ] 5.3 Refactor `templates/tasks/_modal_detail.html`
    - Replace `alert()` call with `showToastNotification()` for nudge validation
    - Add ARIA attributes to modal elements
    - Replace inline styles with utility/component classes
    - _Requirements: 4.4, 4.5, 8.3, 8.6_

  - [ ] 5.4 Refactor `templates/tasks/board.html`
    - Replace inline styles on filter selects with `.filter-select` class
    - Replace inline styles on badge elements with `.badge-pill-sm` class
    - Replace inline styles on action buttons with `.btn-action-compact` class
    - Add `aria-label` to filter select elements
    - _Requirements: 5.5, 5.6, 7.4, 11.3_

  - [ ] 5.5 Refactor `templates/tasks/calendar.html`
    - Replace inline styles on filter selects with `.filter-select` class
    - Replace inline styles on action buttons with `.btn-action-compact` class
    - Add `aria-label` to filter select elements
    - _Requirements: 5.5, 5.6, 7.4, 11.3_

- [ ] 6. Checkpoint - Verify alert replacement and template changes
  - Ensure zero `alert()` calls remain in all `.html` templates and `.js` static files
  - Verify toast notifications render correctly in both light and dark mode
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Dashboard and layout shift improvements
  - [ ] 7.1 Refactor `templates/core/dashboard.html`
    - Add `.chart-container` class to all chart wrapper divs for min-height reservation
    - Replace inline styles on scope switcher buttons with `.scope-switcher-btn` class
    - Replace inline styles on badge elements with `.badge-pill-sm` class
    - Replace arbitrary inline padding/margin with spacing token classes
    - Ensure chart container dimensions remain stable during data load and failure states
    - _Requirements: 2.1, 2.6, 5.5, 5.6, 10.3, 10.4_

  - [ ] 7.2 Add Chart.js dark mode color configuration
    - Create or update `getChartColors()` helper that reads `data-mode` attribute
    - Return dark grid color (12% opacity), light label color, dark tooltip background
    - Ensure chart label and tooltip text maintain 4.5:1 contrast ratio
    - Apply surface color matching card container background
    - File: `templates/core/dashboard.html` (inline script) or `static/js/`
    - _Requirements: 1.4, 12.4_

  - [ ] 7.3 Add modal loading state class
    - Apply `.modal-body-loading` class to task detail modal body during async load
    - Remove class once content is loaded
    - File: `templates/tasks/_modal_detail.html` or relevant modal template
    - _Requirements: 2.2_

- [ ] 8. Apply spacing tokens and card padding consistency
  - [ ] 8.1 Replace arbitrary spacing in glass-card components
    - Audit all elements using `.glass-card` class
    - Replace inline padding with spacing token classes (`p-token-3` through `p-token-5`)
    - Ensure each distinct card type uses a single consistent token value
    - Files: Various templates using `.glass-card`
    - _Requirements: 10.3, 10.5_

  - [ ] 8.2 Apply consistent section margins
    - Replace arbitrary margin between page sections with spacing token classes
    - Ensure same-level sibling sections use the same token value
    - Files: Dashboard, task list, and other main content templates
    - _Requirements: 10.4, 10.5_

- [ ] 9. Verify dark mode, responsive, and theme preservation
  - [ ] 9.1 Verify dark mode toggle performance and flash prevention
    - Confirm dark mode applies within 300ms without page reload
    - Confirm no flash of light-mode on initial page load when `data-mode="dark"` is set
    - Confirm AJAX-loaded fragments inherit dark mode without flash
    - _Requirements: 1.7, 1.8, 1.9_

  - [ ] 9.2 Verify organization theme preservation
    - Confirm all 17 color themes in `THEME_COLOR_MAP` apply correctly in both modes
    - Confirm `--primary`, `--primary-light`, `--primary-dark` values remain unchanged in dark mode
    - _Requirements: 1.6, 12.1_

  - [ ] 9.3 Verify existing functionality preservation
    - Confirm `showConfirmModal()` works with all parameters (title, message, icon, button text, class, password)
    - Confirm sidebar collapse/expand persists to localStorage and restores before first paint
    - Confirm all Chart.js charts render with loading spinners, data binding, and responsive resize
    - Confirm toast notification system (Django messages) auto-dismisses after 4 seconds
    - Confirm AJAX content patterns (task detail modal, comments, dynamic filters) work correctly
    - Confirm skeleton loading CSS (shimmer animation, dark mode override) renders correctly
    - Confirm no JS function in base.html throws errors (`toggleSidebarMin`, `toggleUserDarkMode`, `showConfirmModal`, `updateTabFavicon`, `loadCharts`)
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8_

- [ ] 10. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.
  - Verify no inline `style` attributes remain for patterns covered by extracted classes
  - Verify zero `alert()` calls across all template and JS files
  - Confirm WCAG 2.1 AA contrast requirements met (4.5:1 text, 3:1 non-text) in both modes

## Notes

- No property-based tests are included as this feature is purely CSS/HTML/JS with no algorithmic logic suitable for PBT
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation of visual correctness
- All changes are additive — existing functionality must remain intact per Requirement 12
- The sidebar synchronous script in `base.html` for layout shift prevention (Req 2.3) already exists and should not be modified
- Full WCAG compliance validation requires manual testing with assistive technologies and expert accessibility review

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "1.5", "1.6", "1.7"] },
    { "id": 2, "tasks": ["3.1", "3.2", "3.3", "4.1", "4.2", "4.3"] },
    { "id": 3, "tasks": ["5.1", "5.2", "5.3", "5.4", "5.5", "7.1", "7.2", "7.3"] },
    { "id": 4, "tasks": ["8.1", "8.2"] },
    { "id": 5, "tasks": ["9.1", "9.2", "9.3"] }
  ]
}
```

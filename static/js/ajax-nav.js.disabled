/**
 * AJAX Navigation System
 * Handles partial page updates via fragment requests, LRU content caching,
 * hover-based prefetching, and History API integration.
 * Exposes: window.CSGNav = { navigate, invalidateCache, prefetch }
 *
 * No third-party dependencies — vanilla JS only.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Configuration
  // ---------------------------------------------------------------------------

  var NAV_CONFIG = {
    /** Selector for the main content container that gets swapped on navigation */
    contentSelector: '.page-content',

    /** Maximum time (ms) to wait for a fetch response before falling back */
    timeout: 8000,

    /** Maximum number of entries in the LRU content cache */
    cacheMaxSize: 10,

    /** Time-to-live (ms) for prefetched cache entries */
    cacheTTL: 30000,

    /** Hover debounce delay (ms) before triggering a prefetch */
    prefetchDelay: 80,

    /** Maximum number of concurrent prefetch requests */
    maxConcurrentPrefetch: 2,

    /** Headers sent with every fragment request to signal content-only response */
    fragmentHeaders: {
      'X-Requested-With': 'XMLHttpRequest',
      'X-Fragment': 'true'
    }
  };

  // ---------------------------------------------------------------------------
  // LRU Cache
  // ---------------------------------------------------------------------------

  /**
   * Simple LRU (Least Recently Used) cache backed by a Map.
   * Map preserves insertion order, so the first entry is the least-recently-used.
   * Memory-only — no localStorage/sessionStorage (Requirement 9.6).
   *
   * @param {number} maxSize - Maximum number of entries the cache can hold.
   */
  function LRUCache(maxSize) {
    this._map = new Map();
    this._maxSize = maxSize;
  }

  /**
   * Get a cache entry by URL.
   * Returns the entry object or null if not found.
   * Promotes the accessed entry to most-recent position (LRU access promotion).
   *
   * @param {string} url - The full URL (including query params) to look up.
   * @returns {{ html: string, title: string, timestamp: number } | null}
   */
  LRUCache.prototype.get = function (url) {
    if (!this._map.has(url)) {
      return null;
    }
    var entry = this._map.get(url);
    // TTL check — discard entries older than cacheTTL
    if ((Date.now() - entry.timestamp) > NAV_CONFIG.cacheTTL) {
      this._map.delete(url);
      return null;
    }
    // LRU promotion: delete and re-insert to move entry to end (most-recent)
    this._map.delete(url);
    this._map.set(url, entry);
    return entry;
  };

  /**
   * Store an entry in the cache keyed by URL.
   * Evicts the least-recently-used entry when at maximum capacity.
   *
   * @param {string} url - The full URL (including query params).
   * @param {{ html: string, title: string }} data - Content and title to cache.
   */
  LRUCache.prototype.set = function (url, data) {
    // If the key already exists, delete it first so re-insertion places it at the end (most-recent)
    if (this._map.has(url)) {
      this._map.delete(url);
    }
    // Evict LRU entry if at capacity
    if (this._map.size >= this._maxSize) {
      var lruKey = this._map.keys().next().value;
      this._map.delete(lruKey);
    }
    this._map.set(url, {
      html: data.html,
      title: data.title,
      timestamp: Date.now()
    });
  };

  /**
   * Check whether a URL exists in the cache.
   *
   * @param {string} url - The URL to check.
   * @returns {boolean}
   */
  LRUCache.prototype.has = function (url) {
    return this._map.has(url);
  };

  /**
   * Remove all entries whose URL contains the given string pattern.
   *
   * @param {string} pattern - Substring to match against cached URLs.
   */
  LRUCache.prototype.invalidate = function (pattern) {
    var self = this;
    this._map.forEach(function (value, key) {
      if (key.indexOf(pattern) !== -1) {
        self._map.delete(key);
      }
    });
  };

  /**
   * Remove all entries from the cache.
   */
  LRUCache.prototype.clear = function () {
    this._map.clear();
  };

  /** @type {LRUCache} Content cache instance */
  var contentCache = new LRUCache(NAV_CONFIG.cacheMaxSize);

  // ---------------------------------------------------------------------------
  // Click Handler — DISABLED: AJAX navigation disabled to prevent rendering issues.
  // All navigation uses standard full-page reloads for reliability.
  // The progress bar and cold-start skeleton still provide loading feedback.
  // ---------------------------------------------------------------------------

  function handleClick(event) {
    // AJAX navigation disabled — let all clicks go through as normal page loads
    return;
  }

  // ---------------------------------------------------------------------------
  // Helper Functions
  // ---------------------------------------------------------------------------

  /**
   * Determine skeleton type from URL path and show it in the content container.
   * @param {string} url - The target URL to determine skeleton type for.
   */
  function showSkeletonForUrl(url) {
    var skeletonId = 'skeleton-dashboard';
    var path = url.split('?')[0].split('#')[0]; // Strip query params and hash

    if (path.indexOf('/tasks/') !== -1 && path.indexOf('board') !== -1) {
      skeletonId = 'skeleton-tasks-board';
    } else if (path.indexOf('/tasks/') !== -1 && path.indexOf('calendar') !== -1) {
      skeletonId = 'skeleton-tasks-calendar';
    } else if (path.indexOf('/tasks/') !== -1) {
      skeletonId = 'skeleton-tasks-list';
    } else if (path.indexOf('/officers/') !== -1) {
      skeletonId = 'skeleton-officers';
    } else if (path.indexOf('/notifications/') !== -1) {
      skeletonId = 'skeleton-notifications';
    } else if (path.indexOf('/dashboard') !== -1 || path === '/') {
      skeletonId = 'skeleton-dashboard';
    }

    var template = document.getElementById(skeletonId);
    var container = document.querySelector(NAV_CONFIG.contentSelector);
    if (template && container) {
      var clone = template.content.cloneNode(true);
      container.innerHTML = '';
      container.appendChild(clone);
    }
  }

  /**
   * Update sidebar `.active` class based on the current URL pathname.
   * Removes `.active` from all sidebar links, then adds it to the link
   * whose `pathname` matches `window.location.pathname`. For URLs starting
   * with `/tasks/`, the Tasks sidebar link is always activated.
   *
   * Can be called from reinitializeContent() and from the popstate handler.
   */
  function updateSidebarActive() {
    var links = document.querySelectorAll('.sidebar-link');
    var currentPath = window.location.pathname;

    links.forEach(function (link) {
      link.classList.remove('active');
    });

    var matched = false;

    // Special case: any /tasks/ URL activates the Tasks sidebar link
    if (currentPath.indexOf('/tasks/') === 0 || currentPath === '/tasks/') {
      links.forEach(function (link) {
        if (link.pathname === '/tasks/' || link.pathname.indexOf('/tasks/') === 0) {
          if (!matched) {
            link.classList.add('active');
            matched = true;
          }
        }
      });
    }

    if (!matched) {
      links.forEach(function (link) {
        if (link.pathname === currentPath) {
          link.classList.add('active');
          matched = true;
        }
      });
    }
  }

  /**
   * Set aria-busy attribute on the content container for accessibility.
   * Screen readers use this to announce when content is loading/loaded.
   * @param {boolean} busy - Whether the container is currently loading content.
   */
  function setAriaBusy(busy) {
    var container = document.querySelector(NAV_CONFIG.contentSelector);
    if (container) {
      container.setAttribute('aria-busy', busy ? 'true' : 'false');
    }
  }

  /**
   * Move focus to the first heading (h4 or h5) in the content container.
   * Assists keyboard navigation users after AJAX content loads.
   */
  function focusContentHeading() {
    var container = document.querySelector(NAV_CONFIG.contentSelector);
    if (!container) return;
    var heading = container.querySelector('h4, h5');
    if (heading) {
      heading.setAttribute('tabindex', '-1');
      heading.focus();
    }
  }

  /**
   * Execute inline <script> tags found within the content container.
   * When HTML is inserted via innerHTML, script tags are not executed by
   * the browser. This function recreates each inline script element so
   * the browser evaluates it.
   */
  function executeInlineScripts() {
    var container = document.querySelector(NAV_CONFIG.contentSelector);
    if (!container) return;

    var scripts = container.querySelectorAll('script');
    scripts.forEach(function (originalScript) {
      // Only execute inline scripts (no src attribute)
      if (originalScript.src) return;

      var newScript = document.createElement('script');
      // Copy attributes (type, etc.) except src
      Array.from(originalScript.attributes).forEach(function (attr) {
        if (attr.name !== 'src') {
          newScript.setAttribute(attr.name, attr.value);
        }
      });
      newScript.textContent = originalScript.textContent;

      // Replace the original non-executing script with the new one
      originalScript.parentNode.replaceChild(newScript, originalScript);
    });
  }

  /**
   * Update active state classes on View Switcher (List/Board/Calendar) and
   * Scope Switcher (My Tasks/All Tasks) buttons based on the current URL.
   * Active link gets `btn-primary-custom`; inactive links get `text-secondary border-0`.
   */
  function updateViewSwitcherActive() {
    var currentPath = window.location.pathname;
    var params = new URLSearchParams(window.location.search);

    // Update View Switcher (List/Board/Calendar)
    var viewLinks = document.querySelectorAll('[data-ajax-nav="view-switch"]');
    viewLinks.forEach(function (link) {
      var isActive = false;
      if (currentPath.indexOf('/tasks/board') !== -1 && link.href.indexOf('/board') !== -1) {
        isActive = true;
      } else if (currentPath.indexOf('/tasks/calendar') !== -1 && link.href.indexOf('/calendar') !== -1) {
        isActive = true;
      } else if (currentPath.indexOf('/tasks/') !== -1 && currentPath.indexOf('/board') === -1 && currentPath.indexOf('/calendar') === -1 && link.href.indexOf('/tasks/') !== -1 && link.href.indexOf('/board') === -1 && link.href.indexOf('/calendar') === -1) {
        isActive = true;
      }

      if (isActive) {
        link.classList.add('btn-primary-custom');
        link.classList.remove('text-secondary', 'border-0');
      } else {
        link.classList.remove('btn-primary-custom');
        link.classList.add('text-secondary', 'border-0');
      }
    });

    // Update Scope Switcher (My Tasks/All Tasks)
    var scope = params.get('scope') || 'my_tasks';
    var scopeLinks = document.querySelectorAll('[data-ajax-nav="scope-switch"]');
    scopeLinks.forEach(function (link) {
      var linkScope = new URL(link.href).searchParams.get('scope') || 'my_tasks';
      if (linkScope === scope) {
        link.classList.add('btn-primary-custom');
        link.classList.remove('text-secondary', 'border-0');
      } else {
        link.classList.remove('btn-primary-custom');
        link.classList.add('text-secondary', 'border-0');
      }
    });
  }

  /**
   * Re-initialize page content after AJAX navigation.
   * - Calls lucide.createIcons() to render icon elements in new content
   * - Executes inline <script> tags from the loaded fragment
   * - Updates sidebar active state to reflect the current URL
   * - Updates View Switcher and Scope Switcher active states
   */
  function reinitializeContent() {
    // 1. Re-render Lucide icons in the new content
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }

    // 2. Execute inline scripts from the fragment response
    executeInlineScripts();

    // 3. Update sidebar active state
    updateSidebarActive();

    // 4. Update View Switcher and Scope Switcher active states
    updateViewSwitcherActive();
  }

  // ---------------------------------------------------------------------------
  // History API — popstate handler for back/forward navigation
  // ---------------------------------------------------------------------------

  /**
   * Handle browser back/forward navigation via the popstate event.
   * Restores content from the cache if available, otherwise re-fetches via navigate().
   *
   * @param {PopStateEvent} event - The popstate event fired by the browser.
   */
  function handlePopState(event) {
    var url = (event.state && event.state.url) ? event.state.url : window.location.href;

    // Set aria-busy while restoring content
    setAriaBusy(true);

    // Check the content cache for the URL
    var cached = contentCache.get(url);

    if (cached) {
      // Restore cached content directly
      var container = document.querySelector(NAV_CONFIG.contentSelector);
      if (container) {
        container.innerHTML = cached.html;
      }

      // Update document title
      if (cached.title) {
        document.title = cached.title + ' | CSG Task Management';
      }

      // Re-initialize content (icons, scripts, sidebar active state)
      reinitializeContent();

      // Clear aria-busy and move focus to heading
      setAriaBusy(false);
      focusContentHeading();
    } else {
      // Not in cache — re-fetch via navigate with popstate flag
      // The popstate flag prevents navigate() from pushing another history entry
      navigate(url, { popstate: true });
    }
  }

  // ---------------------------------------------------------------------------
  // Network Quality Detection
  // ---------------------------------------------------------------------------

  /**
   * Check whether the device is on a slow connection (2G or slower).
   * Uses the Network Information API (supported in Chrome/Edge/Android).
   * Returns false (assume fast) when the API is not available.
   *
   * @returns {boolean} True if the connection is slow-2g or 2g.
   */
  function isSlowConnection() {
    var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (!conn) return false; // API not available, assume fast connection
    var type = conn.effectiveType;
    return type === 'slow-2g' || type === '2g';
  }

  // ---------------------------------------------------------------------------
  // Prefetch Controller
  // ---------------------------------------------------------------------------

  /** Timer reference for the current hover debounce (stored on the link element) */
  var prefetchTimer = null;

  /** Number of currently in-flight prefetch requests */
  var activePrefetches = 0;

  /**
   * Determine whether a link is eligible for prefetching.
   * Only sidebar navigation links and view switcher links qualify.
   * Excludes links inside dynamic content areas (task lists, officer cards, modals).
   *
   * @param {HTMLAnchorElement} link - The link element to check.
   * @returns {boolean} True if the link is prefetch-eligible.
   */
  function isPrefetchEligible(link) {
    return link.classList.contains('sidebar-link') ||
           (link.closest('.btn-group') && link.hasAttribute('href'));
  }

  /**
   * Handle mouseenter on prefetch-eligible links.
   * Starts an 80ms debounce timer before initiating a prefetch.
   * @param {MouseEvent} event
   */
  function handleLinkMouseEnter(event) {
    // Skip prefetching on slow connections (2G or slower)
    if (isSlowConnection()) return;

    var link = event.target.closest('a');
    if (!link) return;

    // Only prefetch sidebar links and view switcher links
    if (!isPrefetchEligible(link)) return;

    var href = link.getAttribute('href');

    // Must have a valid href
    if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;

    // Must be same-origin
    if (link.hostname !== window.location.hostname) return;

    // Skip if already cached
    if (contentCache.has(link.href)) return;

    // Start debounce timer (80ms)
    link._prefetchTimer = setTimeout(function () {
      link._prefetchTimer = null;
      doPrefetch(link.href);
    }, NAV_CONFIG.prefetchDelay);
  }

  /**
   * Handle mouseleave on prefetch-eligible links.
   * Cancels the debounce timer if the user moves away before 80ms.
   * @param {MouseEvent} event
   */
  function handleLinkMouseLeave(event) {
    var link = event.target.closest('a');
    if (!link) return;

    if (link._prefetchTimer) {
      clearTimeout(link._prefetchTimer);
      link._prefetchTimer = null;
    }
  }

  /**
   * Perform the actual prefetch for a URL.
   * Fetches the content fragment in the background and stores it in the cache.
   * Silently discards failures (no user-visible error).
   * @param {string} url - The URL to prefetch.
   */
  function doPrefetch(url) {
    // Skip prefetching on slow connections (2G or slower)
    if (isSlowConnection()) return;

    // Respect concurrency limit
    if (activePrefetches >= NAV_CONFIG.maxConcurrentPrefetch) return;

    // Skip if already cached
    if (contentCache.has(url)) return;

    activePrefetches++;

    fetch(url, {
      headers: NAV_CONFIG.fragmentHeaders
    })
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        if (!response.headers.get('X-Fragment-Response')) throw new Error('Not a fragment');
        var title = response.headers.get('X-Page-Title') || '';
        return response.text().then(function (html) {
          return { html: html, title: title };
        });
      })
      .then(function (data) {
        contentCache.set(url, { html: data.html, title: data.title });
      })
      .catch(function () {
        // Silently discard prefetch failures
      })
      .finally(function () {
        activePrefetches--;
      });
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Navigate to a URL via AJAX fragment loading.
   * @param {string} url - The target URL to navigate to.
   * @param {Object} [options] - Navigation options (e.g., { replace: true, popstate: true }).
   */
  function navigate(url, options) {
    options = options || {};

    // 1. Set aria-busy for accessibility (loading state begins)
    setAriaBusy(true);

    // 2. Start progress bar
    if (window.CSGProgress) window.CSGProgress.start();

    // 3. Show skeleton for the target page type
    showSkeletonForUrl(url);

    // 4. Check cache — display cached content immediately on hit
    var cached = contentCache.get(url);
    if (cached) {
      var container = document.querySelector(NAV_CONFIG.contentSelector);
      if (container) {
        container.innerHTML = cached.html;
      }

      // Update document title
      if (cached.title) {
        document.title = cached.title + ' | CSG Task Management';
      }

      // Clear aria-busy (content loaded)
      setAriaBusy(false);

      // Complete progress bar
      if (window.CSGProgress) window.CSGProgress.complete();

      // Push history state (unless popstate or replace)
      if (!options.replace && !options.popstate) {
        history.pushState({ url: url }, '', url);
      }

      // Re-initialize content (lucide icons, inline scripts, sidebar active state)
      reinitializeContent();

      // Move focus to heading for keyboard/screen reader users
      focusContentHeading();
      return;
    }

    // 5. Create AbortController for timeout
    var controller = new AbortController();
    var timeoutId = setTimeout(function () {
      controller.abort();
    }, NAV_CONFIG.timeout);

    // 6. Fetch with fragment headers
    fetch(url, {
      headers: NAV_CONFIG.fragmentHeaders,
      signal: controller.signal
    })
      .then(function (response) {
        clearTimeout(timeoutId);
        if (!response.ok) throw new Error('HTTP ' + response.status);
        // Check if the response is a fragment (has the X-Fragment-Response header)
        // If not, the view doesn't support fragment responses — fall back to full-page nav
        if (!response.headers.get('X-Fragment-Response')) {
          throw new Error('Not a fragment response');
        }
        var title = response.headers.get('X-Page-Title') || '';
        return response.text().then(function (html) {
          return { html: html, title: title };
        });
      })
      .then(function (data) {
        // 7. Store fetched content in cache
        contentCache.set(url, { html: data.html, title: data.title });

        // 8. Swap content
        var container = document.querySelector(NAV_CONFIG.contentSelector);
        if (container) {
          container.innerHTML = data.html;
        }

        // 9. Clear aria-busy now that content is loaded
        setAriaBusy(false);

        // 10. Update document title
        if (data.title) {
          document.title = data.title + ' | CSG Task Management';
        }

        // 11. Complete progress bar
        if (window.CSGProgress) window.CSGProgress.complete();

        // 12. Push state first so window.location reflects the new URL
        //    (needed for updateSidebarActive to read the correct pathname)
        if (!options.replace && !options.popstate) {
          history.pushState({ url: url }, '', url);
        }

        // 13. Re-initialize (lucide icons, inline scripts, sidebar active state)
        reinitializeContent();

        // 14. Move focus to heading for keyboard/screen reader users
        focusContentHeading();
      })
      .catch(function (error) {
        clearTimeout(timeoutId);
        // Fallback to full-page navigation
        setAriaBusy(false);
        if (window.CSGProgress) window.CSGProgress.complete();
        window.location.href = url;
      });
  }

  /**
   * Invalidate cached entries whose URL matches the given pattern.
   * @param {string} pattern - A substring or pattern to match against cached URLs.
   */
  function invalidateCache(pattern) {
    if (pattern) {
      contentCache.invalidate(pattern);
    } else {
      contentCache.clear();
    }
  }

  /**
   * Prefetch a URL's content fragment in the background.
   * @param {string} url - The URL to prefetch.
   */
  function prefetch(url) {
    if (url) {
      doPrefetch(url);
    }
  }

  // ---------------------------------------------------------------------------
  // Form Submission Handler — invalidates task cache on task mutations
  // ---------------------------------------------------------------------------

  /**
   * Listen for form submissions in the tasks section.
   *
   * For GET forms (filters/search): intercept the submission, serialize form
   * data to a query string, and navigate via AJAX to the filtered URL.
   * This avoids a full-page reload when applying or clearing filters.
   *
   * For POST forms (create/edit/delete): allow normal submission but
   * invalidate all task-related cached entries so stale pages are not served.
   *
   * @param {Event} event - The submit event.
   */
  function handleFormSubmit(event) {
    var form = event.target;
    if (!form || form.tagName !== 'FORM') return;

    var action = form.action || window.location.href;

    // For GET forms in the tasks section, use AJAX navigation
    var method = (form.method || 'GET').toUpperCase();
    if (method === 'GET' && action.indexOf('/tasks/') !== -1) {
      event.preventDefault();
      var formData = new FormData(form);
      var params = new URLSearchParams(formData).toString();
      var targetUrl = action.split('?')[0] + (params ? '?' + params : '');
      navigate(targetUrl);
      return;
    }

    // For POST forms that modify tasks, just invalidate the cache
    if (action.indexOf('/tasks/') !== -1) {
      contentCache.invalidate('/tasks/');
    }
  }

  // ---------------------------------------------------------------------------
  // Initialization
  // ---------------------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', function () {
    // AJAX navigation disabled — only keeping history state for potential future use
    history.replaceState({ url: window.location.href }, '', window.location.href);

    // All AJAX click interception, form interception, prefetch, and popstate
    // handlers are disabled. Navigation uses standard full-page reloads.
  });

  // ---------------------------------------------------------------------------
  // Expose public API
  // ---------------------------------------------------------------------------

  window.CSGNav = {
    navigate: navigate,
    invalidateCache: invalidateCache,
    prefetch: prefetch
  };
})();

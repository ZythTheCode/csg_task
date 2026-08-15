/**
 * Progress Bar Controller
 * Manages the top navigation progress bar (#nav-progress) for AJAX navigation feedback.
 * Exposes: window.CSGProgress = { start, set, complete }
 */
(function () {
  'use strict';

  var bar = document.getElementById('nav-progress');
  var indeterminateTimer = null;
  var completeTimer = null;

  /**
   * startProgress()
   * Shows the progress bar at ~15%, starts a timer that adds the indeterminate
   * animation class after 500ms if the request hasn't completed yet.
   */
  function startProgress() {
    if (!bar) return;

    // Clear any pending timers from a previous cycle
    clearTimeout(indeterminateTimer);
    clearTimeout(completeTimer);

    // Reset state
    bar.classList.remove('active');
    bar.style.transition = 'none';
    bar.style.opacity = '1';
    bar.style.width = '0';

    // Force reflow so the reset takes effect before animating
    void bar.offsetWidth;

    // Animate to ~15%
    bar.style.transition = 'width .3s ease';
    bar.style.width = '15%';
    bar.setAttribute('aria-valuenow', '15');

    // After 500ms without completion, switch to indeterminate animation
    indeterminateTimer = setTimeout(function () {
      bar.classList.add('active');
    }, 500);
  }

  /**
   * setProgress(percent)
   * Sets the bar width to a specific percentage. Removes indeterminate animation
   * if it was active. Updates aria-valuenow.
   * @param {number} percent - Value between 0 and 100
   */
  function setProgress(percent) {
    if (!bar) return;

    // Clamp value
    var value = Math.max(0, Math.min(100, percent));

    // Remove indeterminate animation since we have a definite value
    bar.classList.remove('active');
    clearTimeout(indeterminateTimer);

    bar.style.transition = 'width .3s ease';
    bar.style.width = value + '%';
    bar.setAttribute('aria-valuenow', String(value));
  }

  /**
   * completeProgress()
   * Animates bar to 100%, clears timers, removes indeterminate class,
   * then fades out after 300ms and resets width to 0.
   */
  function completeProgress() {
    if (!bar) return;

    // Clear indeterminate timer
    clearTimeout(indeterminateTimer);
    clearTimeout(completeTimer);

    // Remove indeterminate animation
    bar.classList.remove('active');

    // Animate to 100%
    bar.style.transition = 'width .3s ease';
    bar.style.width = '100%';
    bar.setAttribute('aria-valuenow', '100');

    // After 300ms, fade out and reset
    completeTimer = setTimeout(function () {
      bar.style.transition = 'opacity .3s ease';
      bar.style.opacity = '0';

      // After fade completes, reset width for next use
      setTimeout(function () {
        bar.style.transition = 'none';
        bar.style.width = '0';
        bar.style.opacity = '1';
        bar.setAttribute('aria-valuenow', '0');
      }, 300);
    }, 300);
  }

  // Expose API globally for use by ajax-nav.js
  window.CSGProgress = {
    start: startProgress,
    set: setProgress,
    complete: completeProgress
  };
})();

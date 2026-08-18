// Inline SVG icons for sort indicators (no lucide.createIcons() dependency)
const SVG_CHEVRON_UP = '<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--primary)"><path d="m18 15-6-6-6 6"/></svg>';
const SVG_CHEVRON_DOWN = '<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--primary)"><path d="m6 9 6 6 6-6"/></svg>';
const SVG_NEUTRAL = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.4"><path d="m7 15 5 5 5-5"/><path d="m7 9 5-5 5 5"/></svg>';

document.addEventListener('DOMContentLoaded', function() {
  const sortableTables = document.querySelectorAll('.table-sortable');
  
  sortableTables.forEach(table => {
    const headers = table.querySelectorAll('.sortable-header');
    const tbody = table.querySelector('tbody');
    if (!tbody || headers.length === 0) return;
    
    // Initialize original order
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.forEach((row, index) => {
      row.dataset.originalIndex = index;
    });
    
    let activeSortColumn = null;
    let activeSortState = 'none'; // 'none', 'asc', 'desc'
    
    headers.forEach(header => {
      header.addEventListener('click', () => {
        const sortKey = header.getAttribute('data-sort-key');
        if (!sortKey) return;
        
        // Logic to cycle: none -> asc -> desc -> none
        if (activeSortColumn !== header) {
          activeSortColumn = header;
          activeSortState = 'asc';
        } else {
          if (activeSortState === 'asc') activeSortState = 'desc';
          else if (activeSortState === 'desc') activeSortState = 'none';
          else activeSortState = 'asc';
        }
        
        // Update sort icons using inline SVGs
        headers.forEach(h => {
          const container = h.querySelector('.sort-icon-container');
          if (container) {
            if (h === activeSortColumn && activeSortState !== 'none') {
              container.innerHTML = activeSortState === 'asc' ? SVG_CHEVRON_UP : SVG_CHEVRON_DOWN;
            } else {
              container.innerHTML = SVG_NEUTRAL;
            }
          }
        });
        
        // Sort rows
        const currentRows = Array.from(tbody.querySelectorAll('tr'));
        
        if (activeSortState === 'none') {
          currentRows.sort((a, b) => parseInt(a.dataset.originalIndex) - parseInt(b.dataset.originalIndex));
        } else {
          currentRows.sort((a, b) => {
            let valA = a.getAttribute(`data-${sortKey}`) || '';
            let valB = b.getAttribute(`data-${sortKey}`) || '';
            
            // Try numeric comparison if both are valid numbers
            if (!isNaN(valA) && !isNaN(valB) && valA.trim() !== '' && valB.trim() !== '') {
              valA = parseFloat(valA);
              valB = parseFloat(valB);
            } else {
              valA = valA.toLowerCase();
              valB = valB.toLowerCase();
            }
            
            let comp = 0;
            if (valA < valB) comp = -1;
            if (valA > valB) comp = 1;
            
            return activeSortState === 'asc' ? comp : -comp;
          });
        }
        
        // Re-append sorted rows
        currentRows.forEach(row => tbody.appendChild(row));

        // Update aria-sort attributes
        headers.forEach(h => {
          if (h === activeSortColumn && activeSortState !== 'none') {
            h.setAttribute('aria-sort', activeSortState === 'asc' ? 'ascending' : 'descending');
          } else {
            h.setAttribute('aria-sort', 'none');
          }
        });
      });
    });
  });

  // --- Scroll affordance for mobile table wrappers ---
  // Toggles .scrolled-end class when user scrolls to the right edge,
  // hiding the fade shadow (handled via CSS ::after pseudo-element).
  const scrollWrappers = document.querySelectorAll('.table-scroll-wrapper');
  scrollWrappers.forEach(function(wrapper) {
    function checkScrollEnd() {
      if (wrapper.scrollLeft + wrapper.clientWidth >= wrapper.scrollWidth - 1) {
        wrapper.classList.add('scrolled-end');
      } else {
        wrapper.classList.remove('scrolled-end');
      }
    }
    // Check on initial load (in case content doesn't overflow)
    checkScrollEnd();
    wrapper.addEventListener('scroll', checkScrollEnd);
  });
});

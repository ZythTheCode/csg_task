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
        
        // Reset all icons
        headers.forEach(h => {
          const container = h.querySelector('.sort-icon-container');
          if (container) {
            if (h === activeSortColumn && activeSortState !== 'none') {
              container.innerHTML = activeSortState === 'asc' 
                ? '<i data-lucide="chevron-up" style="width:13px;height:13px;color:var(--primary)"></i>'
                : '<i data-lucide="chevron-down" style="width:13px;height:13px;color:var(--primary)"></i>';
            } else {
              container.innerHTML = '<i data-lucide="arrow-up-down" style="width:12px;height:12px;opacity:0.4"></i>';
            }
          }
        });
        
        if (window.lucide) lucide.createIcons();
        
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
      });
    });
  });
});

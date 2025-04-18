document.addEventListener('DOMContentLoaded', function() {
    const applyFiltersButton = document.getElementById('apply_filters_btn');
    const applicationsTableBody = document.getElementById('applications_table_body');
    const statusCheckboxes = document.querySelectorAll('.filter-status');
    const programSelect = document.getElementById('filter_program');

    function applyFilters() {
        if (!applicationsTableBody) return; 
        const selectedStatuses = [];
        statusCheckboxes.forEach(checkbox => {
            if (checkbox.checked) {
                selectedStatuses.push(checkbox.value);
            }
        });

        const selectedProgram = programSelect.value;
        const rows = applicationsTableBody.querySelectorAll('tr');

        rows.forEach(row => {
            if (row.hasAttribute('data-status')) {
                const rowStatus = row.getAttribute('data-status');
                const rowProgram = row.getAttribute('data-program');

                const statusMatch = selectedStatuses.length === 0 || selectedStatuses.includes(rowStatus);
                const programMatch = selectedProgram === "" || rowProgram === selectedProgram;

                if (statusMatch && programMatch) {
                    row.style.display = ''; 
                } else {
                    row.style.display = 'none'; 
                }
            }
        });
    }

    if (applyFiltersButton) {
        applyFiltersButton.addEventListener('click', applyFilters);
    }

    applyFilters();
});
// Products Filtering & Search JS helpers
document.addEventListener('DOMContentLoaded', function () {
    const filterForm = document.getElementById('product-filter-form');
    if (filterForm) {
        const selects = filterForm.querySelectorAll('select');
        selects.forEach(select => {
            select.addEventListener('change', () => {
                filterForm.submit();
            });
        });
    }
});

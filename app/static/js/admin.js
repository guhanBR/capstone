// Admin Dashboard & Management JS
document.addEventListener('DOMContentLoaded', function () {
    console.log('SparePro Admin Module Initialized');
});

function toggleAdminSidebar() {
    const sidebar = document.getElementById('adminSidebar');
    const backdrop = document.getElementById('adminSidebarBackdrop');
    if (sidebar) {
        sidebar.classList.toggle('mobile-open');
    }
    if (backdrop) {
        backdrop.classList.toggle('show');
    }
}


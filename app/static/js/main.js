// SparePro Main JS Library

document.addEventListener('DOMContentLoaded', function () {
    initToasts();
    initModals();
    initConfirmations();
});

// Toast System
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 350px;
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `alert alert-${type}`;
    toast.style.cssText = `
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin: 0;
        animation: slideIn 0.3s ease;
    `;
    toast.innerHTML = `
        <span>${message}</span>
        <button style="background:none;border:none;color:inherit;cursor:pointer;font-weight:bold;margin-left:10px;" onclick="this.parentElement.remove()">✕</button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Modal Helpers
function initModals() {
    document.querySelectorAll('[data-modal-target]').forEach(trigger => {
        trigger.addEventListener('click', e => {
            e.preventDefault();
            const targetId = trigger.getAttribute('data-modal-target');
            const modal = document.getElementById(targetId);
            if (modal) modal.style.display = 'flex';
        });
    });

    document.querySelectorAll('.modal-close, .modal-backdrop').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
        });
    });
}

// Confirmation dialog helper for destructive actions
function initConfirmations() {
    document.querySelectorAll('[data-confirm]').forEach(btn => {
        btn.addEventListener('click', function (e) {
            const msg = this.getAttribute('data-confirm') || 'Are you sure you want to perform this action?';
            if (!confirm(msg)) {
                e.preventDefault();
            }
        });
    });
}

// Account Dropdown Toggle Handler
function toggleAccountMenu(event) {
    if (event) event.stopPropagation();
    const container = document.querySelector('.account-dropdown-container');
    if (container) {
        container.classList.toggle('show');
    }
}

document.addEventListener('click', function (e) {
    const container = document.querySelector('.account-dropdown-container');
    if (container && !container.contains(e.target)) {
        container.classList.remove('show');
    }
});

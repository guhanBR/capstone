// Cart Interactivity

function addToCartAjax(productId, quantity = 1) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    const formData = new FormData();
    formData.append('product_id', productId);
    formData.append('quantity', quantity);

    fetch('/cart/add', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(async res => {
        let data;
        try {
            data = await res.json();
        } catch (e) {
            data = { success: false, message: 'Unexpected server response.' };
        }
        return { ok: res.ok, data };
    })
    .then(({ ok, data }) => {
        if (ok && data.success) {
            showToast(data.message, 'success');
            const cartBadge = document.getElementById('nav-cart-count');
            if (cartBadge) {
                cartBadge.textContent = data.cart_count;
            }
        } else {
            showToast(data.message || 'Could not add to cart.', 'warning');
        }
    })
    .catch(err => {
        showToast('Network error adding product to cart.', 'danger');
    });
}

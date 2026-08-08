from app import db
from app.models.order import Order, OrderItem
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.address import Address
from app.models.inventory import InventoryTransaction
from app.models.notification import Notification
from app.utils.helpers import generate_order_number, log_audit
from app.utils.constants import (
    ORDER_STATUS_PENDING, ORDER_STATUS_CONFIRMED, ORDER_STATUS_PROCESSING,
    ORDER_STATUS_PACKED, ORDER_STATUS_SHIPPED, ORDER_STATUS_DELIVERED,
    ORDER_STATUS_CANCELLED, INVENTORY_TYPE_SALE, INVENTORY_TYPE_RETURN
)

class OrderService:
    @staticmethod
    def create_order(user_id, address_id, payment_method='Cash on Delivery'):
        address = db.session.get(Address, address_id)
        if not address or address.user_id != user_id:
            return False, "Invalid shipping address selected.", None

        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart or not cart.items:
            return False, "Your shopping cart is empty.", None

        # Server-side validation of stock and status
        subtotal = 0.0
        order_items_data = []

        for item in cart.items:
            product = item.product
            if not product or product.status != 'active':
                return False, f"Product '{product.name if product else 'Unknown'}' is no longer available.", None

            if product.stock_quantity < item.quantity:
                return False, f"Insufficient stock for '{product.name}'. Available: {product.stock_quantity}, Requested: {item.quantity}.", None

            unit_price = product.effective_price
            item_subtotal = unit_price * item.quantity
            subtotal += item_subtotal

            order_items_data.append({
                'product': product,
                'quantity': item.quantity,
                'unit_price': unit_price,
                'subtotal': item_subtotal
            })

        shipping_charge = 0.0 if subtotal >= 2000 else 100.0  # Free shipping over ₹2000
        discount = 0.0
        total_amount = subtotal + shipping_charge - discount
        order_num = generate_order_number()

        # Atomic Transaction
        try:
            order = Order(
                user_id=user_id,
                order_number=order_num,
                address_id=address.id,
                subtotal=subtotal,
                discount=discount,
                shipping_charge=shipping_charge,
                total_amount=total_amount,
                payment_method=payment_method,
                payment_status='Pending' if payment_method == 'Cash on Delivery' else 'Paid',
                order_status=ORDER_STATUS_PENDING
            )
            db.session.add(order)
            db.session.flush()

            for data in order_items_data:
                product = data['product']
                qty = data['quantity']

                # Create OrderItem snapshot
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    sku=product.sku,
                    quantity=qty,
                    unit_price=data['unit_price'],
                    subtotal=data['subtotal']
                )
                db.session.add(order_item)

                # Deduct inventory stock
                prev_stock = product.stock_quantity
                new_stock = prev_stock - qty
                product.stock_quantity = new_stock

                # Create inventory transaction
                inv_trans = InventoryTransaction(
                    product_id=product.id,
                    transaction_type=INVENTORY_TYPE_SALE,
                    quantity=qty,
                    previous_quantity=prev_stock,
                    new_quantity=new_stock,
                    reference_type='Order',
                    reference_id=order.id,
                    notes=f"Order {order.order_number} placed by user #{user_id}"
                )
                db.session.add(inv_trans)

            # Clear cart items
            CartItem.query.filter_by(cart_id=cart.id).delete()

            # Create notification for customer
            notif = Notification(
                user_id=user_id,
                title="Order Placed Successfully",
                message=f"Your order {order.order_number} for ₹{total_amount:,.2f} has been placed.",
                type="success"
            )
            db.session.add(notif)

            db.session.commit()
            return True, "Order placed successfully!", order
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to place order: {str(e)}", None

    @staticmethod
    def update_order_status(order_id, new_status, admin_id):
        order = db.session.get(Order, order_id)
        if not order:
            return False, "Order not found."

        old_status = order.order_status
        if old_status == new_status:
            return True, "Order status is already up to date."

        try:
            # Handle cancellation & stock return if order is cancelled
            if new_status == ORDER_STATUS_CANCELLED and old_status != ORDER_STATUS_CANCELLED:
                for item in order.items:
                    if item.product:
                        prev_stock = item.product.stock_quantity
                        new_stock = prev_stock + item.quantity
                        item.product.stock_quantity = new_stock

                        inv_trans = InventoryTransaction(
                            product_id=item.product.id,
                            transaction_type=INVENTORY_TYPE_RETURN,
                            quantity=item.quantity,
                            previous_quantity=prev_stock,
                            new_quantity=new_stock,
                            reference_type='Order Cancellation',
                            reference_id=order.id,
                            notes=f"Stock restored due to cancellation of Order {order.order_number}"
                        )
                        db.session.add(inv_trans)

            order.order_status = new_status
            if new_status == ORDER_STATUS_DELIVERED and order.payment_method == 'Cash on Delivery':
                order.payment_status = 'Paid'

            # Customer notification
            notif = Notification(
                user_id=order.user_id,
                title=f"Order Update: {new_status}",
                message=f"Status for your order {order.order_number} has been updated to '{new_status}'.",
                type="info" if new_status != ORDER_STATUS_DELIVERED else "success"
            )
            db.session.add(notif)

            db.session.commit()
            log_audit(admin_id, 'UPDATE_STATUS', 'Order', order.id, f"Order {order.order_number} status changed from {old_status} to {new_status}")
            return True, f"Order status updated to {new_status}."
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to update order status: {str(e)}"

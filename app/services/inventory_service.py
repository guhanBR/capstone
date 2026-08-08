from app import db
from app.models.product import Product
from app.models.inventory import InventoryTransaction
from app.utils.helpers import log_audit

class InventoryService:
    @staticmethod
    def adjust_stock(product_id, new_quantity, transaction_type, notes, admin_id):
        product = db.session.get(Product, product_id)
        if not product:
            return False, "Product not found."

        try:
            new_qty = int(new_quantity)
            if new_qty < 0:
                return False, "Stock quantity cannot be negative."
        except ValueError:
            return False, "Invalid quantity."

        prev_qty = product.stock_quantity
        diff = new_qty - prev_qty

        try:
            product.stock_quantity = new_qty
            inv_trans = InventoryTransaction(
                product_id=product.id,
                transaction_type=transaction_type,
                quantity=abs(diff),
                previous_quantity=prev_qty,
                new_quantity=new_qty,
                reference_type='Manual Adjustment',
                notes=notes or 'Manual stock adjustment by admin'
            )
            db.session.add(inv_trans)
            db.session.commit()

            log_audit(admin_id, 'INVENTORY_ADJUST', 'Product', product.id, f"Stock for {product.name} adjusted from {prev_qty} to {new_qty} ({transaction_type})")
            return True, f"Stock updated to {new_qty}."
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to adjust stock: {str(e)}"

import pandas as pd
import numpy as np
from app.models.order import Order, OrderItem
from app.models.product import Product

class ProductAnalytics:
    @staticmethod
    def get_product_performance():
        items = OrderItem.query.join(Order).filter(Order.order_status != 'Cancelled').all()
        if not items:
            return {
                'best_sellers': [],
                'category_revenue': [],
                'product_summary_df': pd.DataFrame(),
                'df': pd.DataFrame()
            }

        data = [{
            'product_id': item.product_id,
            'product_name': item.product_name,
            'sku': item.sku,
            'category_name': item.product.category.name if item.product and item.product.category else 'Uncategorized',
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'subtotal': float(item.subtotal)
        } for item in items]

        df = pd.DataFrame(data)

        # Aggregate per product
        product_summary = df.groupby(['product_id', 'product_name', 'sku', 'category_name']).agg(
            total_qty_sold=('quantity', 'sum'),
            total_revenue=('subtotal', 'sum'),
            avg_unit_price=('unit_price', 'mean')
        ).reset_index()

        # Sort with Pandas & calculate percentages using NumPy
        product_summary = product_summary.sort_values(by='total_revenue', ascending=False)
        total_rev_array = product_summary['total_revenue'].to_numpy()
        grand_total = np.sum(total_rev_array) if len(total_rev_array) > 0 else 1.0

        product_summary['revenue_percentage'] = np.round((total_rev_array / grand_total) * 100, 2)

        # Category revenue aggregation
        category_summary = df.groupby('category_name')['subtotal'].agg(['sum', 'count']).reset_index()
        category_summary.columns = ['Category', 'Revenue', 'ItemsSold']

        return {
            'best_sellers': product_summary.to_dict('records'),
            'category_revenue': category_summary.to_dict('records'),
            'product_summary_df': product_summary
        }

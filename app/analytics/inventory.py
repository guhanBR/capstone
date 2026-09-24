import pandas as pd
import numpy as np
from app.models.product import Product
from app.models.inventory import InventoryTransaction

class InventoryAnalytics:
    @staticmethod
    def get_inventory_status():
        products = Product.query.all()
        if not products:
            return {
                'total_products': 0,
                'total_inventory_value': 0.0,
                'low_stock_count': 0,
                'out_of_stock_count': 0,
                'low_stock_items': [],
                'out_of_stock_items': [],
                'products_summary': [],
                'df': pd.DataFrame()
            }

        data = [{
            'product_id': p.id,
            'sku': p.sku,
            'name': p.name,
            'category_name': p.category.name if p.category else 'N/A',
            'price': float(p.price),
            'stock_quantity': p.stock_quantity,
            'minimum_stock_level': p.minimum_stock_level,
            'status': p.status,
            'stock_status': p.stock_status,
            'inventory_value': float(p.price) * p.stock_quantity
        } for p in products]

        df = pd.DataFrame(data)

        prices = df['price'].to_numpy()
        stocks = df['stock_quantity'].to_numpy()
        values = df['inventory_value'].to_numpy()

        total_value = float(np.sum(values))
        low_stock_mask = (stocks > 0) & (stocks <= df['minimum_stock_level'].to_numpy())
        out_of_stock_mask = stocks <= 0

        low_stock_count = int(np.sum(low_stock_mask))
        out_of_stock_count = int(np.sum(out_of_stock_mask))

        return {
            'total_products': len(df),
            'total_inventory_value': round(total_value, 2),
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'low_stock_items': df[low_stock_mask].to_dict('records'),
            'out_of_stock_items': df[out_of_stock_mask].to_dict('records'),
            'products_summary': df.to_dict('records'),
            'df': df
        }

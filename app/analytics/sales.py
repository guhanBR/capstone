import pandas as pd
import numpy as np
from app import db
from app.models.order import Order, OrderItem

class SalesAnalytics:
    @staticmethod
    def get_sales_summary():
        orders = Order.query.filter(Order.order_status != 'Cancelled').all()
        if not orders:
            return {
                'total_sales': 0.0,
                'total_orders': 0,
                'average_order_value': 0.0,
                'sales_by_status': [],
                'daily_sales': [],
                'monthly_sales': [],
                'daily_sales_df': pd.DataFrame(),
                'monthly_sales_df': pd.DataFrame(),
                'df': pd.DataFrame()
            }

        data = [{
            'order_id': o.id,
            'order_number': o.order_number,
            'total_amount': float(o.total_amount),
            'subtotal': float(o.subtotal),
            'order_status': o.order_status,
            'created_at': o.created_at,
            'date': o.created_at.strftime('%Y-%m-%d'),
            'month': o.created_at.strftime('%Y-%m')
        } for o in orders]

        df = pd.DataFrame(data)

        # NumPy numerical calculations
        total_amounts = df['total_amount'].to_numpy()
        total_sales = float(np.sum(total_amounts))
        total_orders = len(orders)
        aov = float(np.mean(total_amounts)) if total_orders > 0 else 0.0

        # Grouping with Pandas
        sales_by_status = df.groupby('order_status')['total_amount'].agg(['count', 'sum']).reset_index().to_dict('records')
        
        daily_sales = df.groupby('date')['total_amount'].agg(['count', 'sum']).reset_index()
        daily_sales.columns = ['Date', 'Orders', 'Revenue']

        monthly_sales = df.groupby('month')['total_amount'].agg(['count', 'sum']).reset_index()
        monthly_sales.columns = ['Month', 'Orders', 'Revenue']

        return {
            'total_sales': round(total_sales, 2),
            'total_orders': total_orders,
            'average_order_value': round(aov, 2),
            'sales_by_status': sales_by_status,
            'daily_sales': daily_sales.to_dict('records'),
            'monthly_sales': monthly_sales.to_dict('records'),
            'df': df
        }

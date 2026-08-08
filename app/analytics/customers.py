import pandas as pd
import numpy as np
from app.models.order import Order
from app.models.user import User

class CustomerAnalytics:
    @staticmethod
    def get_customer_insights():
        orders = Order.query.join(User).filter(User.role == 'customer', Order.order_status != 'Cancelled').all()
        if not orders:
            return {
                'top_customers': [],
                'summary_stats': {'total_active_customers': 0, 'avg_customer_ltv': 0.0},
                'df': pd.DataFrame()
            }

        data = [{
            'user_id': o.user_id,
            'customer_name': o.user.name,
            'customer_email': o.user.email,
            'order_id': o.id,
            'total_amount': float(o.total_amount)
        } for o in orders]

        df = pd.DataFrame(data)

        cust_summary = df.groupby(['user_id', 'customer_name', 'customer_email']).agg(
            total_orders=('order_id', 'count'),
            total_spent=('total_amount', 'sum'),
            avg_order_value=('total_amount', 'mean')
        ).reset_index()

        cust_summary = cust_summary.sort_values(by='total_spent', ascending=False)

        spent_array = cust_summary['total_spent'].to_numpy()
        avg_ltv = float(np.mean(spent_array)) if len(spent_array) > 0 else 0.0

        return {
            'top_customers': cust_summary.to_dict('records'),
            'summary_stats': {
                'total_active_customers': len(cust_summary),
                'avg_customer_ltv': round(avg_ltv, 2)
            },
            'df': cust_summary
        }

import io
import datetime
from app.analytics import SalesAnalytics, ProductAnalytics, CustomerAnalytics, InventoryAnalytics

class ReportService:
    @staticmethod
    def generate_sales_csv():
        sales_data = SalesAnalytics.get_sales_summary()
        df = sales_data.get('df')
        
        output = io.StringIO()
        if df is not None and not df.empty:
            df.to_csv(output, index=False)
        else:
            output.write("order_id,order_number,total_amount,subtotal,order_status,created_at,date,month\n")
        
        filename = f"sales_report_{datetime.datetime.now().strftime('%Y_%m_%d')}.csv"
        return output.getvalue(), filename

    @staticmethod
    def generate_products_csv():
        prod_data = ProductAnalytics.get_product_performance()
        df = prod_data.get('product_summary_df')
        
        output = io.StringIO()
        if df is not None and not df.empty:
            df.to_csv(output, index=False)
        else:
            output.write("product_id,product_name,sku,category_name,total_qty_sold,total_revenue,avg_unit_price,revenue_percentage\n")
        
        filename = f"product_performance_report_{datetime.datetime.now().strftime('%Y_%m_%d')}.csv"
        return output.getvalue(), filename

    @staticmethod
    def generate_customers_csv():
        cust_data = CustomerAnalytics.get_customer_insights()
        df = cust_data.get('df')
        
        output = io.StringIO()
        if df is not None and not df.empty:
            df.to_csv(output, index=False)
        else:
            output.write("user_id,customer_name,customer_email,total_orders,total_spent,avg_order_value\n")
        
        filename = f"customer_report_{datetime.datetime.now().strftime('%Y_%m_%d')}.csv"
        return output.getvalue(), filename

    @staticmethod
    def generate_inventory_csv():
        inv_data = InventoryAnalytics.get_inventory_status()
        df = inv_data.get('df')
        
        output = io.StringIO()
        if df is not None and not df.empty:
            df.to_csv(output, index=False)
        else:
            output.write("product_id,sku,name,category_name,price,stock_quantity,minimum_stock_level,status,stock_status,inventory_value\n")
        
        filename = f"inventory_report_{datetime.datetime.now().strftime('%Y_%m_%d')}.csv"
        return output.getvalue(), filename

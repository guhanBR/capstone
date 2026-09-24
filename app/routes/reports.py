from flask import Blueprint, render_template, Response, make_response
from flask_login import login_required
from app.utils.decorators import manager_or_admin_required
from app.analytics import SalesAnalytics, ProductAnalytics, CustomerAnalytics, InventoryAnalytics
from app.services.report_service import ReportService

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
@manager_or_admin_required
def analytics_dashboard():
    sales = SalesAnalytics.get_sales_summary()
    products = ProductAnalytics.get_product_performance()
    customers = CustomerAnalytics.get_customer_insights()
    inventory = InventoryAnalytics.get_inventory_status()

    return render_template(
        'admin/reports.html',
        sales=sales,
        products=products,
        customers=customers,
        inventory=inventory
    )


@reports_bp.route('/export/sales')
@login_required
@manager_or_admin_required
def export_sales_csv():
    csv_data, filename = ReportService.generate_sales_csv()
    response = make_response(csv_data)
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv'
    return response


@reports_bp.route('/export/products')
@login_required
@manager_or_admin_required
def export_products_csv():
    csv_data, filename = ReportService.generate_products_csv()
    response = make_response(csv_data)
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv'
    return response


@reports_bp.route('/export/customers')
@login_required
@manager_or_admin_required
def export_customers_csv():
    csv_data, filename = ReportService.generate_customers_csv()
    response = make_response(csv_data)
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv'
    return response


@reports_bp.route('/export/inventory')
@login_required
@manager_or_admin_required
def export_inventory_csv():
    csv_data, filename = ReportService.generate_inventory_csv()
    response = make_response(csv_data)
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv'
    return response

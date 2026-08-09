import pytest
from app import create_app, db
from app.models.category import Category
from app.models.product import Product
from app.services.product_service import ProductService

@pytest.fixture
def filter_client():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        cat1 = Category(name="Bearings", status="active")
        cat2 = Category(name="Mechanical Seals", status="active")
        db.session.add_all([cat1, cat2])
        db.session.flush()

        # Seed products matching example in requirement prompt
        p1 = Product(category_id=cat1.id, name="Product A", sku="P-A", brand="SKF", price=300, stock_quantity=10, description="Bearing A")
        p2 = Product(category_id=cat1.id, name="Product B", sku="P-B", brand="SKF", price=780, stock_quantity=10, description="Bearing B")
        p3 = Product(category_id=cat1.id, name="Product C", sku="P-C", brand="SKF", price=1050, stock_quantity=10, description="Bearing C")
        p4 = Product(category_id=cat1.id, name="Product D", sku="P-D", brand="SKF", price=2500, stock_quantity=10, description="Bearing D")
        p5 = Product(category_id=cat2.id, name="Product E", sku="P-E", brand="Burgmann", price=3500, stock_quantity=10, description="Seal E")
        p6 = Product(category_id=cat2.id, name="Product F", sku="P-F", brand="Burgmann", price=4900, stock_quantity=10, description="Seal F")
        p7 = Product(category_id=cat2.id, name="Product G", sku="P-G", brand="Burgmann", price=5500, stock_quantity=10, description="Seal G")
        p8 = Product(category_id=cat2.id, name="Product H", sku="P-H", brand="Burgmann", price=6900, stock_quantity=10, description="Seal H")
        
        db.session.add_all([p1, p2, p3, p4, p5, p6, p7, p8])
        db.session.commit()

        yield app.test_client()
        db.session.remove()
        db.drop_all()

def test_price_filter_4900(filter_client):
    res = filter_client.get('/products/?max_price=4900&ajax=1')
    assert res.status_code == 200
    # Should contain products A..F (prices 300, 780, 1050, 2500, 3500, 4900)
    assert b'Product A' in res.data
    assert b'Product B' in res.data
    assert b'Product C' in res.data
    assert b'Product D' in res.data
    assert b'Product E' in res.data
    assert b'Product F' in res.data
    # Should HIDE G (5500) and H (6900)
    assert b'Product G' not in res.data
    assert b'Product H' not in res.data

def test_price_filter_1000(filter_client):
    res = filter_client.get('/products/?max_price=1000&ajax=1')
    assert res.status_code == 200
    assert b'Product A' in res.data
    assert b'Product B' in res.data
    assert b'Product C' not in res.data
    assert b'Product F' not in res.data

def test_price_filter_500(filter_client):
    res = filter_client.get('/products/?max_price=500&ajax=1')
    assert res.status_code == 200
    assert b'Product A' in res.data
    assert b'Product B' not in res.data

def test_category_and_price_filter(filter_client):
    # Category 1 (Bearings) + max_price 2000
    res = filter_client.get('/products/?category=1&max_price=2000&ajax=1')
    assert res.status_code == 200
    assert b'Product A' in res.data
    assert b'Product B' in res.data
    assert b'Product C' in res.data      # 1050 <= 2000
    assert b'Product D' not in res.data  # 2500 > 2000
    assert b'Product E' not in res.data  # Category 2

def test_brand_and_price_filter(filter_client):
    # Brand = SKF + max_price = 2000
    res = filter_client.get('/products/?brand=SKF&max_price=2000&ajax=1')
    assert res.status_code == 200
    assert b'Product A' in res.data
    assert b'Product B' in res.data
    assert b'Product C' in res.data
    assert b'Product D' not in res.data # 2500 > 2000
    assert b'Product E' not in res.data # Burgmann

def test_search_and_price_filter(filter_client):
    # Search = Bearing + max_price = 2000
    res = filter_client.get('/products/?q=Bearing&max_price=2000&ajax=1')
    assert res.status_code == 200
    assert b'Product A' in res.data
    assert b'Product B' in res.data
    assert b'Product C' in res.data
    assert b'Product D' not in res.data # 2500 > 2000
    assert b'Product E' not in res.data # Seal E

def test_price_filter_sorting(filter_client):
    res = filter_client.get('/products/?max_price=4900&sort=price_asc&ajax=1')
    assert res.status_code == 200
    assert b'Product A' in res.data
    assert b'Product G' not in res.data

def test_ajax_partial_response(filter_client):
    res = filter_client.get('/products/?max_price=4900&ajax=1', headers={'X-Requested-With': 'XMLHttpRequest'})
    assert res.status_code == 200
    assert b'<html' not in res.data
    assert b'Product A' in res.data
    assert b'Product G' not in res.data

def test_max_price_db():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        cat = Category(name="Test", status="active")
        db.session.add(cat)
        db.session.flush()
        db.session.add(Product(category_id=cat.id, name="P1", sku="P1", brand="B", price=6900, stock_quantity=1, description="D"))
        db.session.commit()
        assert ProductService.get_max_price() == 6900.0
        db.session.remove()
        db.drop_all()

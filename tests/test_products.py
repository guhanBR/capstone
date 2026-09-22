import pytest
from app import create_app, db
from app.models.category import Category
from app.models.product import Product

@pytest.fixture
def client():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        cat = Category(name="Bearings", status="active")
        db.session.add(cat)
        db.session.flush()

        p1 = Product(category_id=cat.id, name="6203 Deep Groove Ball Bearing", sku="BRG-6203", brand="SKF", price=200, stock_quantity=15, description="Desc")
        p2 = Product(category_id=cat.id, name="25mm Mechanical Seal", sku="SEAL-25", brand="Burgmann", price=450, stock_quantity=5, description="Seal")
        db.session.add_all([p1, p2])
        db.session.commit()

        yield app.test_client()
        db.session.remove()
        db.drop_all()

def test_product_search(client):
    res = client.get('/products/?q=6203')
    assert res.status_code == 200
    assert b'6203 Deep Groove Ball Bearing' in res.data
    assert b'25mm Mechanical Seal' not in res.data

def test_product_detail(client):
    res = client.get('/products/1')
    assert res.status_code == 200
    assert b'BRG-6203' in res.data
    assert b'/static/images/products/' in res.data

def test_product_image_url():
    p1 = Product(image="bearing.svg")
    p2 = Product(image="https://example.com/photo.jpg")
    p3 = Product(image="")
    assert p1.image_url == "/static/images/products/bearing.svg"
    assert p2.image_url == "https://example.com/photo.jpg"
    assert p3.image_url == "/static/images/products/placeholder.svg"


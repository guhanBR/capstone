from datetime import datetime
from app import db

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    brand = db.Column(db.String(80), nullable=False, index=True)
    model_number = db.Column(db.String(80), nullable=True)
    description = db.Column(db.Text, nullable=False)
    specifications = db.Column(db.Text, nullable=True)
    compatibility = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_price = db.Column(db.Numeric(10, 2), nullable=True)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    minimum_stock_level = db.Column(db.Integer, nullable=False, default=5)
    image = db.Column(db.String(255), default='placeholder.png')
    status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cart_items = db.relationship('CartItem', backref='product', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='product', lazy=True, cascade='all, delete-orphan')
    inventory_transactions = db.relationship('InventoryTransaction', backref='product', lazy=True, cascade='all, delete-orphan')

    @property
    def effective_price(self):
        if self.discount_price and float(self.discount_price) > 0 and float(self.discount_price) < float(self.price):
            return float(self.discount_price)
        return float(self.price)

    @property
    def stock_status(self):
        if self.stock_quantity <= 0:
            return 'Out of Stock'
        elif self.stock_quantity <= self.minimum_stock_level:
            return 'Low Stock'
        return 'In Stock'

    @property
    def average_rating(self):
        approved_reviews = [r for r in self.reviews if r.status == 'approved']
        if not approved_reviews:
            return 0.0
        return round(sum(r.rating for r in approved_reviews) / len(approved_reviews), 1)

    @property
    def review_count(self):
        return len([r for r in self.reviews if r.status == 'approved'])

    @property
    def image_url(self):
        if not self.image:
            return '/static/images/products/placeholder.png'
        if self.image.startswith(('http://', 'https://', '/')):
            return self.image
        if self.image.startswith('static/'):
            return f'/{self.image}'
        return f'/static/images/products/{self.image}'

    def to_dict(self):
        return {
            'id': self.id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else '',
            'name': self.name,
            'sku': self.sku,
            'brand': self.brand,
            'model_number': self.model_number,
            'description': self.description,
            'specifications': self.specifications,
            'compatibility': self.compatibility,
            'price': float(self.price),
            'discount_price': float(self.discount_price) if self.discount_price else None,
            'effective_price': self.effective_price,
            'stock_quantity': self.stock_quantity,
            'minimum_stock_level': self.minimum_stock_level,
            'stock_status': self.stock_status,
            'image': self.image,
            'image_url': self.image_url,
            'status': self.status,
            'rating': self.average_rating,
            'review_count': self.review_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

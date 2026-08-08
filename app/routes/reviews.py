from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.utils.decorators import customer_required
from app import db
from app.models.review import Review
from app.models.order import Order, OrderItem
from app.models.product import Product

reviews_bp = Blueprint('reviews', __name__)

@reviews_bp.route('/add/<int:order_id>/<int:product_id>', methods=['GET', 'POST'])
@login_required
@customer_required
def add_review(order_id, product_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    
    # Ensure product was actually in this delivered/completed order
    order_item = OrderItem.query.filter_by(order_id=order.id, product_id=product_id).first_or_404()
    product = db.session.get(Product, product_id)

    # Check for existing review
    existing_review = Review.query.filter_by(user_id=current_user.id, product_id=product_id, order_id=order_id).first()
    if existing_review:
        flash('You have already submitted a review for this item in this order.', 'info')
        return redirect(url_for('orders.order_detail', order_number=order.order_number))

    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        review_text = request.form.get('review_text', '').strip()

        if not rating or rating < 1 or rating > 5:
            flash('Please select a rating between 1 and 5 stars.', 'danger')
            return render_template('customer/reviews.html', order=order, product=product)

        review = Review(
            user_id=current_user.id,
            product_id=product_id,
            order_id=order_id,
            rating=rating,
            review_text=review_text,
            status='approved'
        )
        db.session.add(review)
        db.session.commit()

        flash('Thank you for reviewing your spare part!', 'success')
        return redirect(url_for('products.product_detail', product_id=product_id))

    return render_template('customer/reviews.html', order=order, product=product)

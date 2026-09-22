import re

def validate_email(email):
    if not email:
        return False, "Email address is required."
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Please enter a valid email address."
    return True, ""

def validate_phone(phone):
    if not phone:
        return False, "Phone number is required."
    # Allow 10-15 digits, spaces, plus, hyphens
    cleaned = re.sub(r'[\s\-\+\(\)]', '', phone)
    if not cleaned.isdigit() or len(cleaned) < 10 or len(cleaned) > 15:
        return False, "Please enter a valid 10-digit phone number."
    return True, ""

def validate_password(password):
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."
    return True, ""

def validate_product_data(data):
    errors = []
    if not data.get('name') or len(data.get('name').strip()) < 3:
        errors.append("Product name must be at least 3 characters long.")
    if not data.get('sku') or len(data.get('sku').strip()) < 2:
        errors.append("SKU code is required.")
    if not data.get('brand'):
        errors.append("Brand name is required.")
    if not data.get('category_id'):
        errors.append("Please select a product category.")
    if not data.get('description') or len(data.get('description', '').strip()) < 3:
        errors.append("Product description is required (at least 3 characters).")

    price = None
    try:
        price = float(data.get('price', 0))
        if price < 0:
            errors.append("Price must be a positive number.")
    except (ValueError, TypeError):
        errors.append("Invalid price format.")

    try:
        stock = int(data.get('stock_quantity', 0))
        if stock < 0:
            errors.append("Stock quantity cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Invalid stock quantity format.")

    # Discount price must be strictly less than regular price
    if data.get('discount_price') and price is not None:
        try:
            dp = float(data['discount_price'])
            if dp < 0:
                errors.append("Discount price cannot be negative.")
            elif dp >= price:
                errors.append("Discount price must be less than the regular price.")
        except (ValueError, TypeError):
            errors.append("Invalid discount price format.")

    return len(errors) == 0, errors

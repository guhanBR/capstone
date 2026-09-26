# SparePro — Online Spare Parts Ordering System for Motors & Pumps

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-Supported-orange.svg)](https://www.mysql.com/)
[![Pandas](https://img.shields.io/badge/Pandas-2.1%2B-150458.svg)](https://pandas.pydata.org/)
[![Tests](https://img.shields.io/badge/Tests-60%20Passing-brightgreen.svg)](tests/)

**SparePro** is a web-based Enterprise Resource Planning (ERP) and e-commerce application designed for ordering, inventory tracking, and sales analytics of industrial motor and pump spare parts.

---

## 📋 Table of Contents
- [Project Overview](#-project-overview)
- [Technology Stack](#-technology-stack)
- [Verified Feature Set](#-verified-feature-set)
  - [Customer Portal](#customer-portal)
  - [Management & ERP Portal](#management--erp-portal)
- [Role-Based Access Control (RBAC)](#-role-based-access-control-rbac)
- [Project Directory Structure](#-project-directory-structure)
- [Installation & Setup Guide](#-installation--setup-guide)
  - [Prerequisites](#1-prerequisites)
  - [Virtual Environment Setup](#2-virtual-environment-setup)
  - [Installing Dependencies](#3-installing-dependencies)
  - [Environment Configuration](#4-environment-configuration)
  - [Database Setup & Seeding](#5-database-setup--seeding)
  - [Running the Application](#6-running-the-application)
- [Default Login Credentials](#-default-login-credentials)
- [Running Automated Tests](#-running-automated-tests)
- [Security & Best Practices](#-security--best-practices)

---

## 🚀 Project Overview

SparePro solves the operational challenges of managing spare parts for industrial motors and pumps—such as impellers, mechanical seals, bearings, copper windings, capacitors, and pump casings. 

The application provides:
- A customer-facing e-commerce storefront for searching, filtering, and ordering spare parts.
- An administrative back-office for product catalog management, inventory tracking with low-stock alerts, order processing, customer administration, and staff management.
- Analytical reporting powered by **Pandas** and **NumPy** for sales trends, inventory turnover, and product performance.

---

## 🛠️ Technology Stack

| Layer | Technology / Library | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core programming language |
| **Web Framework** | Flask 3.0+ | Web application framework |
| **ORM & DB** | Flask-SQLAlchemy 3.1+, PyMySQL 1.1+ | MySQL primary connection, SQLite fallback |
| **Data Analytics** | Pandas 2.1+, NumPy 1.26+ | Data frames, sales aggregation, numerical reporting |
| **Auth & Security**| Flask-Login 0.6+, Flask-WTF 1.2+, Werkzeug 3.0+ | Session management, CSRF protection, password hashing |
| **Frontend** | HTML5, Vanilla CSS3, JavaScript (ES6) | Responsive UI with custom themes (dark/light) |
| **Testing** | Pytest 7.4+ | Automated test suite (60 test cases) |

---

## ✅ Verified Feature Set

### Customer Portal
- **Product Browsing & Search**: Search by keywords, filter by category, brand, stock availability, and dynamic price ranges (`min_price`, `max_price`), with custom sorting (price asc/desc, newest).
- **Product Specifications & Details**: Detailed product views with technical specs, stock status, discount badges, and customer reviews.
- **Shopping Cart**: Add to cart, quantity management, live cart item counter, and summary calculations.
- **Buy Now & Express Checkout**: Direct single-item checkout or full cart checkout with shipping address creation and payment method selection (COD, Net Banking, UPI, Cards).
- **Order Tracking & History**: Order confirmation with unique order numbers (`ORD-...`), itemized invoices, status tracking, and cancellation for pending orders.
- **User Profile & Address Book**: Manage contact details, default shipping addresses, and theme preference (Dark/Light mode).
- **Wishlist Management**: Save items for later and transfer wishlist items directly to cart.
- **Product Reviews**: Submit 1–5 star ratings and reviews for purchased products.

### Management & ERP Portal
- **Admin Dashboard**: Overview metrics for revenue, total orders, pending orders, total customers, low-stock warnings, and recent order activity.
- **Product Catalog Management**: Add, edit, and deactivate products with image upload validation (safe MIME checking).
- **Category & Brand Management**: Organize spare parts into categories and brands.
- **Inventory Management & Audit Log**: Track stock levels, set minimum stock thresholds, record manual stock adjustments (restock, reduction, correction), and audit history.
- **Order Management & Fulfillment**: Process customer orders through status transitions (`Pending` → `Processing` → `Shipped` → `Delivered` / `Cancelled`).
- **Customer Management**: View registered customers, search profiles, order history, and toggle user active/inactive status.
- **Staff Management**: Owner/Admin restricted management of Manager and Employee accounts.
- **Reviews Moderation**: Approve, hide, or delete customer reviews.
- **Analytics & Reports**: Sales summary reports, monthly trends, product performance, customer metrics, and CSV report export.

---

## 🔐 Role-Based Access Control (RBAC)

The application enforces fine-grained role permissions via custom decorators (`@admin_required`, `@manager_or_admin_required`, `@staff_required`, `@customer_required`):

| Role | Catalog & Inventory | Order Processing | Financial Analytics | Staff Management |
| :--- | :---: | :---: | :---: | :---: |
| **Owner / Admin** | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **Manager** | ✅ Full | ✅ Full | ✅ Full | ❌ Restricted |
| **Employee** | 👁️ View / Update Stock | ✅ Update Status | ❌ Restricted | ❌ Restricted |
| **Customer** | 🛒 Storefront Only | 📦 Own Orders | ❌ Restricted | ❌ Restricted |

---

## 📁 Project Directory Structure

```
DEF capstone/
├── app/
│   ├── analytics/              # Data analysis using Pandas & NumPy
│   │   ├── __init__.py
│   │   ├── customers.py
│   │   ├── inventory.py
│   │   ├── products.py
│   │   └── sales.py
│   ├── models/                 # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── address.py
│   │   ├── audit_log.py
│   │   ├── cart.py
│   │   ├── category.py
│   │   ├── contact_message.py
│   │   ├── inventory.py
│   │   ├── notification.py
│   │   ├── order.py
│   │   ├── product.py
│   │   ├── review.py
│   │   ├── user.py
│   │   └── wishlist.py
│   ├── routes/                 # Blueprint route handlers
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── api.py
│   │   ├── auth.py
│   │   ├── cart.py
│   │   ├── customer.py
│   │   ├── orders.py
│   │   ├── products.py
│   │   ├── reports.py
│   │   └── reviews.py
│   ├── services/               # Business logic services
│   │   ├── auth_service.py
│   │   ├── inventory_service.py
│   │   ├── notification_service.py
│   │   ├── order_service.py
│   │   ├── product_service.py
│   │   └── report_service.py
│   ├── static/                 # Static assets (CSS, JS, uploads)
│   │   ├── css/
│   │   │   ├── admin.css
│   │   │   ├── customer.css
│   │   │   ├── main.css
│   │   │   ├── responsive.css
│   │   │   └── themes.css
│   │   ├── images/
│   │   └── js/
│   │       ├── admin.js
│   │       ├── cart.js
│   │       ├── main.js
│   │       ├── products.js
│   │       └── theme.js
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── admin/
│   │   ├── auth/
│   │   ├── customer/
│   │   ├── errors/
│   │   └── base.html
│   ├── utils/                  # Helper functions & RBAC decorators
│   │   ├── constants.py
│   │   ├── decorators.py
│   │   ├── helpers.py
│   │   └── validators.py
│   └── __init__.py             # Application factory & setup
├── seed/                       # Database seeding script
│   └── seed_data.py
├── tests/                      # Pytest test suite
│   ├── test_admin_dashboard.py
│   ├── test_auth.py
│   ├── test_buy_now.py
│   ├── test_cart.py
│   ├── test_customer_features.py
│   ├── test_order_flow.py
│   ├── test_orders.py
│   ├── test_price_filter_requirements.py
│   ├── test_products.py
│   └── test_rbac.py
├── .env.example
├── .gitignore
├── config.py
├── requirements.txt
├── run.py
├── schema.sql
└── sparepro.db
```

---

## ⚙️ Installation & Setup Guide

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.14.2)
- **MySQL Server 8.0+** (or SQLite fallback)
- **Git**

### 2. Virtual Environment Setup
Open PowerShell or Command Prompt in the project root:

```powershell
# Create a virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Or Windows Command Prompt (cmd)
venv\Scripts\activate.bat
```

### 3. Installing Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the root directory by copying `.env.example`:

```bash
# Windows Command Prompt / PowerShell
copy .env.example .env
```

Edit `.env` with your environment values:
```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your_secure_secret_key_here

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=sparepro_db
MYSQL_USER=your_db_user
MYSQL_PASSWORD=your_db_password
DATABASE_URL=mysql+pymysql://your_db_user:your_db_password@localhost:3306/sparepro_db

# Application Configuration
ITEMS_PER_PAGE=12
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
```

> ℹ️ **Note on SQLite Fallback**: If MySQL environment variables are omitted or MySQL is unavailable, the application automatically falls back to `sparepro.db`.

### 5. Database Setup & Seeding

1. **Create MySQL Database**:
   ```sql
   CREATE DATABASE sparepro_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. **Run Seeding Script**:
   ```bash
   python -m seed.seed_data
   ```

### 6. Running the Application
```bash
python run.py
```
Or using Flask CLI:
```bash
flask run --host=127.0.0.1 --port=5000
```

Access the application in your web browser at:
`http://127.0.0.1:5000`

---

## 🔑 Default Login Credentials

After running `seed_data.py`, use these pre-configured accounts for testing:

| Role | Email | Default Password |
| :--- | :--- | :--- |
| **Admin / Owner** | `admin@sparepro.local` | `Admin@12345` |
| **Manager** | `manager@sparepro.local` | `Manager@12345` |
| **Employee** | `employee@sparepro.local` | `Employee@12345` |
| **Customer** | `rajesh.kumar@example.com` | `Customer@123` |

---

## 🧪 Running Automated Tests

Run the complete test suite with **pytest**:

```bash
pytest
```

To run a specific test file:
```bash
pytest tests/test_rbac.py
```

---

## 🛡️ Security & Best Practices

- **Password Hashing**: Passwords are securely hashed using Werkzeug's `generate_password_hash`.
- **CSRF Protection**: Form submissions protected via `Flask-WTF` CSRF token verification.
- **Upload Safety**: Image uploads are restricted to `.jpg`, `.jpeg`, `.png`, `.webp` with UUID renaming and MIME type validation.
- **Secret Hygiene**: Sensitive credentials stored in `.env` (excluded via `.gitignore`).

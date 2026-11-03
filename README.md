# PharmaCare — Pharmacy Management System (PMS)

A production-quality, full-stack web application designed to automate the end-to-end daily operations of a modern medical store and pharmacy: medicine inventory, atomic POS billing, supplier management, strict expiry blocking, customer backorders, credit dues with fine calculations, returns with quality verification quarantine, e-prescriptions, and executive analytics.

---

## 1. Tech Stack

- **Backend:** Python 3 (Flask 3.1, Flask-SQLAlchemy, Flask-Login, Werkzeug Security)
- **Database:** SQLite (Structured with SQLAlchemy ORM, foreign keys, cascades, and ready for PostgreSQL/MySQL via `DATABASE_URL`)
- **Frontend:** Modern Responsive UI powered by Tailwind CSS, FontAwesome 6, Lucide Icons, Alpine.js, and Chart.js (zero build step required)
- **Authentication & Security:** Session-based RBAC with PBKDF2/SHA256 salted password hashing, input sanitization, and route-level guards
- **Payments:** Integrated Mock Payment Gateway simulating Razorpay / Stripe checkout (Card, UPI, Net Banking with success/failure simulation)

---

## 2. Pre-Configured Demo Credentials

The database comes pre-seeded with sample medicines, suppliers, bills, and user accounts:

| Role | Email | Password | User ID | Description |
|---|---|---|---|---|
| **Admin (Shop Owner)** | `admin@pharmacy.com` | `admin123` | `ADM-1001` | Full administrative control, reports, inventory pricing, staff management |
| **Pharmacist** | `pharmacist@pharmacy.com` | `pharma123` | `PHR-2001` | Daily counter operations, POS billing, stock monitoring, dues collection |

*Note: You can also use the **"New Staff / Pharmacy Registration"** page (`/auth/signup`) to create new admin or pharmacist accounts. User IDs are automatically generated and displayed on a dedicated registration confirmation screen.*

---

## 3. Core Modules & Features

### 1. User Management & RBAC
- Role-Based Access Control protecting both web routes and JSON API endpoints.
- Auto-generated User IDs (e.g. `ADM-XXXX`, `PHR-XXXX`) displayed upon sign-up.
- Admin staff dashboard to create new pharmacists and toggle active/deactivated access.

### 2. Medicine & Inventory Management
- Full catalog with category, generic formula, batch number, manufacturer, shelf/rack location.
- Real-time stock status computation: `In Stock`, `Low Stock` (at or below reorder threshold), and `Out of Stock`.
- Soft-delete support (`is_discontinued=True`) preserving relational integrity for historical invoices.

### 3. POS Billing & Thermal / A4 Invoices
- Fast POS terminal with instant keyboard search, barcode scanning support, and live autocomplete.
- Atomic database transactions with rollback on failure — stock is deducted immediately and negative stock is strictly prevented.
- Dynamic calculation of line item subtotals, configurable discount %, and GST/Tax %.
- Professional, printable invoice view with `@media print` CSS for receipts.

### 4. Automated Expiry Surveillance & POS Block
- Dedicated Expiry Tracking Center (`/medicines/expiry`).
- Nearing Expiry alerts (< 30 days) with countdown badges and value-at-risk analysis.
- **Strict POS Block:** Expired medicines cannot be billed or added to carts.

### 5. Supplier Procurement & Auto-Restock
- Supplier directory with contact details and product categories.
- Purchase Order workflow: Draft $\to$ Ordered $\to$ Received.
- One-click "Receive & Restock" that automatically increments sellable inventory and checks customer backorders.

### 6. Customer Backorders & Reservations
- Patients can reserve out-of-stock medications directly through the customer portal (`/customer/reserve`).
- When a shipment is received from suppliers or inventory is replenished, the system automatically detects pending reservations and flags an in-app restock alert.

### 7. Returns with Quality Verification Hold
- Returns are quarantined under `Pending Quality Verification` upon receipt.
- Items are **never** auto-added directly to sellable stock. A pharmacist or admin must inspect the returned item:
  - **Approved & Restocked:** Stock is safely restored to inventory.
  - **Rejected & Damaged:** Quarantined or discarded (not restocked).

### 8. Credit Dues & ₹10/day Overdue Fines
- Tracks credit and partial payments with due dates.
- Overdue accounts past their due date automatically accumulate a fine of **₹10/day**.
- Dedicated Dues Settlement screen (`/bills/dues`) to record payments against outstanding balances.

### 9. Customer E-Prescription Portal
- Public portal (`/customer/`) where patients can check medicine availability.
- Upload prescription image/PDF with doctor's notes.
- Pharmacist verification queue (`/admin/prescriptions`) to inspect prescription attachments, approve or reject, and convert to a POS sale.

### 10. Executive Reports & Charts
- Interactive Chart.js analytics:
  - 7-Day Sales & Profit Trends (Revenue vs Gross Profit)
  - Departmental Sales Distribution (Doughnut chart)
  - Stock Health Breakdown
- Financial ledger with Gross Revenue, COGS, Discounts, GST/Tax, and Net Margins.

### 11. In-App Notification Center
- Slide-out notification drawer with live alerts for:
  - Expired and near-expiry medicines
  - Low stock items needing replenishment
  - Overdue credit bills
  - Returns awaiting quality verification
  - Pending customer prescriptions
  - Restocked medicines with customer reservations

---

## 4. Setup & Running Instructions

### Prerequisites
- Python 3.10+ (Tested on Python 3.14 on Windows)
- pip package manager

### Installation

1. Navigate to the project directory:
   ```powershell
   cd C:\Users\shyam\.gemini\antigravity\scratch\pharmacy_management_system
   ```

2. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Seed the database with sample medicines, suppliers, bills, and demo users:
   ```powershell
   python seed_data.py
   ```

4. Start the web application:
   ```powershell
   python app.py
   ```

5. Open your browser and visit:
   ```
   http://localhost:5000
   ```

---

## 5. Running Automated Unit Tests

Run the test suite covering billing calculations, atomic stock deduction, negative stock prevention, expiry blocking, return workflows, and overdue fines:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

All 9 test suites run in-memory and execute in under 2 seconds.

---

## 6. Directory Structure

```
pharmacy_management_system/
├── app.py                     # Flask application factory, error handlers, blueprints
├── config.py                  # Environment config, upload paths, tax rates, fines
├── models.py                  # SQLAlchemy ORM models & relationships
├── seed_data.py               # Database seeder (22 medicines, suppliers, bills, users)
├── requirements.txt           # Python dependencies
├── api/                       # REST APIs for POS search, mock gateway, charts, alerts
│   ├── __init__.py
│   └── routes.py
├── auth/                      # Authentication & RBAC module
│   ├── __init__.py
│   └── routes.py
├── routes/                    # Server-rendered controllers
│   ├── main.py                # Landing page & POS terminal route
│   ├── admin.py               # Admin dashboard, staff users, reports, prescription review
│   ├── pharmacist.py          # Pharmacist counter dashboard
│   ├── medicines.py           # Medicine inventory, CRUD, expiry tracking
│   ├── suppliers.py           # Supplier directory & purchase orders
│   ├── bills.py               # Invoices, printable receipts, dues ledger
│   ├── returns.py             # Returns logging & quality verification
│   └── customer.py            # Public medicine search, reservations, e-prescription upload
├── services/                  # Encapsulated business logic
│   ├── billing_service.py     # Atomicity, tax/discount math, stock deduction, settlements
│   ├── inventory_service.py   # Restocking, reservations check, return verification
│   ├── expiry_service.py      # Near-expiry and expired tracking
│   └── alert_service.py       # Notification center aggregation
├── static/
│   ├── css/style.css          # Custom print styles (@media print) & scrollbars
│   ├── js/pos.js              # POS terminal cart, calculations, keyboard search
│   └── js/alerts.js           # Live notification drawer controller
├── templates/                 # Jinja2 responsive templates with Tailwind CSS
│   ├── base.html              # Base layout with navbar, sidebar, and notification drawer
│   ├── landing.html           # Public landing page
│   ├── auth/                  # Login, signup, registration confirmation
│   ├── dashboard/             # Admin and Pharmacist dashboards
│   ├── pos/                   # Point-of-Sale terminal
│   ├── medicines/             # Catalog, form, and expiry center
│   ├── suppliers/             # Supplier directory & purchase orders
│   ├── bills/                 # Invoices, printable receipt, and dues tracker
│   ├── returns/               # Returns list and logging form
│   ├── customer/              # Public portal, reserve form, e-prescription upload
│   ├── reports/               # Financial & profit analysis
│   ├── users/                 # Staff directory & role management
│   └── errors/                # 404, 403, 500 pages
├── tests/                     # Unit test suites
│   ├── test_billing_and_inventory.py
│   └── test_expiry_and_dues.py
└── uploads/prescriptions/     # Stored customer prescription documents
```

---

## 7. License & Compliance
Designed in accordance with pharmaceutical inventory and retail dispensing standards. All sensitive credentials are hashed, transactions are ACID-compliant, and patient prescriptions are handled through dedicated review channels.

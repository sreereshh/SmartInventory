# Project Documentation – Smart Inventory & Order Management System

## 1. Architecture

```
                         ┌──────────────────────────────┐
 Browser (Bootstrap 5) ──►  Django templates + views    │
                         │  (session login, CSRF)       │
                         │                              │      ┌────────────┐
 Android app (Kotlin) ───►  Django REST Framework       ├──────►  SQLite     │
   Retrofit + token      │  (Token auth, Swagger)       │      └────────────┘
                         │                              │
                         │  Service layer (shared):     │
                         │   inventory.services         │
                         │   orders.services            │
                         │   reports.services           │
                         └──────────────────────────────┘
```

The web pages and the REST API call the **same service layer**, so business rules (stock can't go
negative, orders are atomic, cancelling restores stock) are implemented exactly once.

## 2. Django apps

| App | Responsibility |
|---|---|
| `config` | Settings (environment driven), root URLs, WSGI/ASGI |
| `core` | Dashboard view, base form mixin, template tags, context processor, `seed_data` command |
| `accounts` | Custom `User` (role: admin/staff), login, logout, registration, user management, `admin_required` decorator |
| `products` | `Category`, `Product` models and CRUD views |
| `inventory` | `StockTransaction`, stock in/out, stock list and history, **`apply_stock` service** |
| `customers` | `Customer` model and CRUD |
| `orders` | `Order`, `OrderItem`, **`create_order` / `change_status` services**, order pages |
| `reports` | Report queries (`services.py`) and printable report pages |
| `api` | DRF serializers, viewsets, permissions, error handler, pagination, Swagger |

## 3. Key design decisions

1. **Stock is changed in exactly one place** – `inventory.services.apply_stock`. It uses a conditional
   `UPDATE … WHERE quantity >= requested`, so concurrent requests cannot oversell, and writes an immutable
   `StockTransaction` (type, reason, quantity before/after, user, linked order).
2. **Negative stock is impossible at three levels**: service validation, the conditional UPDATE, and the
   `PositiveIntegerField` (database `CHECK >= 0`).
3. **Orders are atomic** – `create_order` runs in `transaction.atomic()`: validate every line, create
   the order, reduce stock, create items, compute totals. Any failure rolls everything back.
4. **Price snapshot** – `OrderItem.unit_price` / `unit_cost` are copied at order time; later price edits do not
   change history or profit reports.
5. **Order lifecycle** – `pending → confirmed → completed`, or `cancelled` from pending/confirmed.
   Cancelling re-adds stock (logged as `order_cancel`). Completed/cancelled orders are final, so stock can't be
   restored twice.
6. **Products can't be edited to change quantity** – use Stock In/Out so the history always reconciles.
7. **Referential integrity** – customers/products that appear in orders are `PROTECT`ed (HTTP 409 / friendly message).
8. **RBAC** – Admin: everything. Staff: operate (create/edit/order/stock) but not delete, no user management.
   Public registration always creates *Staff*; only admins can promote users.
9. **Secrets** – read from environment variables / `.env`; the app refuses to start with `DEBUG=False` and the default key.

## 4. Database

See `../ER_Diagram/er_diagram.png` (source: `er_diagram.mmd`, renders on GitHub).

Constraints in the schema: unique `Product.code`, `Category.name`, `Order.order_number`; `CHECK` prices ≥ 0,
`OrderItem.quantity ≥ 1`, `StockTransaction.quantity > 0`, `Order.total_amount ≥ 0`; unique `(order, product)`
per order item; indexes on names, codes, status and created dates.

## 5. Feature checklist (requirement → where it lives)

| Requirement | Implemented in |
|---|---|
| Login / logout / registration, hashed passwords | `accounts/` (PBKDF2-SHA256, Django validators) |
| Admin & Staff roles, RBAC, protected dashboard | `accounts/models.py`, `accounts/decorators.py`, `api/permissions.py` |
| Dashboard (all stats from DB) | `core/views.py`, `reports/services.dashboard_data`, `templates/dashboard.html` |
| Product CRUD, search, categories | `products/` |
| Stock in/out, history, low-stock alerts, validation | `inventory/` |
| Customer CRUD + search | `customers/` |
| Orders (multi-product, totals, auto stock, history, details, status) | `orders/` |
| Reports (daily, monthly, total, inventory, low stock, order) + print | `reports/` (Print button / print CSS) |
| REST API + token auth + Swagger | `api/` |
| Android app | `android/SmartInventoryAndroid/` |
| Tests | `*/tests.py` (72 tests) |

## 6. Testing summary

* **72 automated Django tests** (`python manage.py test`) covering auth, RBAC, product/customer CRUD, stock in/out,
  negative-stock prevention, order creation, rollback on insufficient stock, cancellation restore, reports and every
  API endpoint (status codes, validation, permissions).
* **Live tests** against a real server: an HTTP script (58 checks) and a real-Chromium browser script (52 checks) – see `backend/live_tests/`.
* **Android**: the Kotlin source was written against the same API contract and cross-checked statically, but it could
  **not be compiled or run** in the environment used to build this project (no Android SDK). See README → Known limitations.

# REST API Reference

Interactive documentation (Swagger UI) is served by the running backend:

| URL | What |
|---|---|
| `http://127.0.0.1:8000/api/docs/` | Swagger UI – try every endpoint in the browser |
| `http://127.0.0.1:8000/api/redoc/` | ReDoc reference |
| `http://127.0.0.1:8000/api/schema/` | Raw OpenAPI 3 schema |
| `openapi.yaml` / `openapi.json` (this folder) | Offline copy of the schema (import into Postman / Insomnia) |

Base URL: `http://127.0.0.1:8000/api/` (Android emulator: `http://10.0.2.2:8000/api/`).

## Authentication

Token authentication (DRF `TokenAuthentication`). Log in, then send the token on every request:

```
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/login/` | none | `{username, password}` → `{token, user}` (401 on bad credentials) |
| POST | `/auth/register/` | none | `{username, email, password, first_name?, last_name?}` → creates a **Staff** user (201) |
| POST | `/auth/logout/` | token | Deletes the token (the token stops working) |
| GET | `/auth/me/` | token | Current user and role |

## Roles and permissions

| Role | Can do |
|---|---|
| **Admin** | Everything, including **deleting** products / categories / customers |
| **Staff** | Read, create and update everything (products, customers, stock, orders). **Cannot delete** (HTTP 403) |

Orders are never deleted or edited – they are cancelled (which restores stock) so history stays accurate.

## Endpoints

List endpoints are paginated: `?page=2&page_size=50` (default 20, max 200) and return
`{"count", "next", "previous", "results": [...]}`. Most support `?search=` and `?ordering=`.

### Categories – `/categories/`
`GET` list · `POST` create · `GET/PUT/PATCH /{id}/` · `DELETE /{id}/` (admin; 409 if it still has products)

### Products – `/products/`
`GET` list (`?search=`, `?category=<id>`, `?status=low|out|ok`) · `POST` create · `GET/PUT/PATCH/DELETE /{id}/`

* `quantity` on **create** is the opening stock (recorded as a stock transaction).
* `quantity` cannot be changed by PUT/PATCH – use the inventory endpoints so history stays correct (400).
* `code` is unique (case-insensitive, stored upper-case); selling price below purchase price is rejected (400).
* `DELETE` returns **409** if the product was ever ordered.

### Customers – `/customers/`
`GET` list (`?search=` name/phone/email/address) · `POST` · `GET/PUT/PATCH/DELETE /{id}/` (delete: admin only, 409 if the customer has orders)

### Inventory

| Method | Path | Description |
|---|---|---|
| GET | `/inventory/stock/` | Current stock for every product (`?status=low|out|ok`, `?category=`, `?search=`) |
| GET | `/inventory/low-stock/` | Low-stock **notifications**: products at/below minimum level (includes out of stock) |
| GET | `/inventory/transactions/` | Stock history (`?product=<id>`, `?type=IN|OUT`, `?search=`) |
| POST | `/inventory/stock-in/` | `{product, quantity, reason?, note?}` → 201, returns `current_quantity` and `low_stock_alert` |
| POST | `/inventory/stock-out/` | Same body. **400** if quantity exceeds stock (negative stock is impossible) |

### Orders – `/orders/`

| Method | Path | Description |
|---|---|---|
| GET | `/orders/` | History (`?status=`, `?customer=`, `?date_from=`, `?date_to=`, `?search=`) |
| GET | `/orders/{id}/` | Details with line items |
| POST | `/orders/` | Create order – see below |
| POST | `/orders/{id}/status/` | `{status}`: pending→confirmed→completed, or pending/confirmed→cancelled (restores stock) |

Create body:

```json
{
  "customer": 1,
  "notes": "Deliver after 5pm",
  "items": [ {"product": 3, "quantity": 2}, {"product": 7, "quantity": 1} ]
}
```

The server calculates unit prices, subtotals and the grand total, reduces stock and writes stock
transactions **inside one database transaction**. If any product has insufficient stock the whole
request fails with **400** and nothing is saved. The 201 response includes `low_stock_alerts` for
products that dropped to/below their minimum level.

### Dashboard – `GET /dashboard/`
Totals (products, customers, orders, sales), low-stock count, sales today / this month / gross profit,
last 7 days, orders by status, top products, inventory value, stock by category, recent orders and
low-stock products – all computed live from the database.

### Reports – `GET /reports/…`

| Path | Parameters |
|---|---|
| `/reports/daily/` | `?date=YYYY-MM-DD` (default today) |
| `/reports/monthly/` | `?month=YYYY-MM` (default this month) |
| `/reports/total-sales/` | – |
| `/reports/inventory/` | `?category=<id>` |
| `/reports/low-stock/` | – |
| `/reports/orders/` | `?date_from=`, `?date_to=`, `?status=`, `?customer=` |

"Sales" always excludes cancelled orders.

## Errors

Every error has the same shape:

```json
{ "detail": "Insufficient stock for Wireless Mouse (ELE-001): available 8, requested 50.",
  "errors": { "items": ["…"] } }
```

| Code | Meaning |
|---|---|
| 200 / 201 / 204 | OK / created / deleted |
| 400 | Validation error (bad input, insufficient stock, invalid status change) |
| 401 | Missing, invalid or revoked token / wrong login |
| 403 | Authenticated but not allowed (e.g. Staff trying to delete) |
| 404 | Record does not exist |
| 405 | Method not allowed (e.g. deleting an order) |
| 409 | Record cannot be deleted because other records depend on it |

## Quick start (Windows PowerShell)

```powershell
# 1. Log in and keep the token
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/login/ `
         -ContentType "application/json" -Body '{"username":"admin","password":"Admin@12345"}'
$h = @{ Authorization = "Token $($login.token)" }

# 2. Read data
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/dashboard/ -Headers $h
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/products/?search=mouse" -Headers $h).results

# 3. Create an order
$body = '{"customer":1,"items":[{"product":2,"quantity":1}]}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/orders/ -Headers $h -ContentType "application/json" -Body $body
```

With curl (use `curl.exe` in PowerShell):

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/auth/login/ -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"Admin@12345\"}"
curl.exe http://127.0.0.1:8000/api/products/ -H "Authorization: Token YOUR_TOKEN"
```

# Smart Inventory – Android app (Kotlin)

Native Android client for the Django REST API.

**Screens:** Login · Dashboard · Products (search) · Stock (search + low/out/in-stock filters) · Customers (search) ·
Orders (search + status filters) · Create order (multi-product, live total) · Order details (confirm / complete / cancel).

**Tech:** Kotlin, XML layouts + ViewBinding, Material 3, Retrofit 2 + Gson, OkHttp, Kotlin coroutines,
`SharedPreferences` for the token. Min SDK 24 (Android 7.0), target/compile SDK 34.

## 1. Requirements
* **Android Studio** Koala (2024.1) or newer – it bundles the JDK 17+ that Gradle needs.
* The Django backend running (see the main README).

## 2. Open and run
1. Android Studio → **File ▸ Open** → select the `android/SmartInventoryAndroid` folder.
2. Wait for **Gradle sync** (first time it downloads Gradle 8.7 and the libraries – internet required).
   If asked, let Android Studio install the **Android SDK 34**.
3. Create an emulator (Device Manager ▸ *Pixel 6*, API 34) or plug in a phone with USB debugging.
4. Start the backend on your PC so it listens on all interfaces:
   ```powershell
   cd SmartInventory\backend
   .\.venv\Scripts\Activate.ps1
   python manage.py runserver 0.0.0.0:8000
   ```
5. Press **Run ▶**. Log in with `admin` / `Admin@12345` (or `staff` / `Staff@12345`).

## 3. Server URL
| Where the app runs | Server URL to type on the login screen |
|---|---|
| Android **emulator** | `http://10.0.2.2:8000/` (default – `10.0.2.2` is the emulator's alias for your PC) |
| **Real phone** on the same Wi-Fi | `http://<your-PC-IP>:8000/` – find the IP with `ipconfig` (IPv4 Address) |

For a real phone also: add the PC IP to `DJANGO_ALLOWED_HOSTS` in `backend/.env`
(e.g. `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,10.0.2.2,192.168.1.10`), restart the server, and allow Python
through Windows Firewall when prompted. The URL is remembered between launches.

## 4. How it works
* `data/ApiService.kt` – Retrofit interface (one function per endpoint).
* `data/ApiClient.kt` – OkHttp client that adds `Authorization: Token …` to every request; `safeCall` turns
  success, HTTP errors (reads the API's `{"detail": …}` message), no network, timeouts and bad URLs into an `ApiResult`.
* `data/SessionManager.kt` – stores token, username, role and server URL.
* A `401` response from any screen clears the session and returns to Login.
* Loading indicators on every screen, pull-to-refresh on lists, Retry buttons on errors.

## 5. Limitations
* Lists load up to **200 rows** per screen (the API page size limit); use the search box to narrow down.
* Read-mostly: stock in/out, product/customer editing and reports are on the website; the app covers
  the essential features requested (login, dashboard, products, stock, customers, create/view orders) plus order status changes.
* Plain `http://` is allowed (`usesCleartextTraffic`) for local development. Use HTTPS in production.
* The token is stored in private app storage (`SharedPreferences`), not the Android Keystore.
* No automated Android tests are included.
* This source was **not compiled** in the build environment (no Android SDK available). If Gradle reports an error
  on first sync, please open an issue – the most likely causes are SDK/Gradle version prompts, which Android Studio can
  fix with *File ▸ Sync Project with Gradle Files*.

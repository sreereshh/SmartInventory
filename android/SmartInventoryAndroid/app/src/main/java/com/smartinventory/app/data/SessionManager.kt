package com.smartinventory.app.data

import android.content.Context

/** Stores the API token, the signed-in user and the server URL in private SharedPreferences. */
class SessionManager(context: Context) {

    private val prefs = context.applicationContext.getSharedPreferences("smart_inventory_session", Context.MODE_PRIVATE)

    var token: String?
        get() = prefs.getString(KEY_TOKEN, null)
        set(value) = prefs.edit().putString(KEY_TOKEN, value).apply()

    var username: String
        get() = prefs.getString(KEY_USERNAME, "") ?: ""
        set(value) = prefs.edit().putString(KEY_USERNAME, value).apply()

    var role: String
        get() = prefs.getString(KEY_ROLE, "") ?: ""
        set(value) = prefs.edit().putString(KEY_ROLE, value).apply()

    var baseUrl: String
        get() = prefs.getString(KEY_BASE_URL, DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
        set(value) = prefs.edit().putString(KEY_BASE_URL, normalizeUrl(value)).apply()

    val isLoggedIn: Boolean get() = !token.isNullOrBlank()

    fun saveLogin(auth: AuthResponse) {
        token = auth.token
        username = auth.user.username
        role = auth.user.role
    }

    /** Forget the login but keep the server URL. */
    fun clear() {
        prefs.edit().remove(KEY_TOKEN).remove(KEY_USERNAME).remove(KEY_ROLE).apply()
    }

    companion object {
        private const val KEY_TOKEN = "token"
        private const val KEY_USERNAME = "username"
        private const val KEY_ROLE = "role"
        private const val KEY_BASE_URL = "base_url"

        /** 10.0.2.2 is the Android emulator's alias for the host PC's localhost. */
        const val DEFAULT_BASE_URL = "http://192.168.220.60:8000/"

        fun normalizeUrl(raw: String): String {
            var url = raw.trim()
            if (url.isEmpty()) return DEFAULT_BASE_URL
            if (!url.startsWith("http://") && !url.startsWith("https://")) url = "http://$url"
            if (!url.endsWith("/")) url += "/"
            return url
        }
    }
}

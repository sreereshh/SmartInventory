package com.smartinventory.app.util

import android.content.Context
import android.content.Intent
import android.widget.Toast
import androidx.core.content.ContextCompat
import com.smartinventory.app.R
import com.smartinventory.app.data.ApiResult
import com.smartinventory.app.data.SessionManager
import com.smartinventory.app.ui.LoginActivity
import java.text.NumberFormat
import java.util.Locale

private val moneyFormat: NumberFormat = NumberFormat.getNumberInstance(Locale("en", "IN")).apply {
    minimumFractionDigits = 2
    maximumFractionDigits = 2
}

fun formatMoney(value: Double): String = "₹" + moneyFormat.format(value)

/** "2026-11-14T10:30:12.123456+05:30" -> "2026-11-14 10:30" */
fun formatDate(iso: String): String = if (iso.length >= 16) iso.substring(0, 16).replace('T', ' ') else iso

fun Context.toast(message: String) = Toast.makeText(this, message, Toast.LENGTH_LONG).show()

/** Colour used for order status badges. */
fun Context.orderStatusColor(status: String): Int = ContextCompat.getColor(
    this,
    when (status) {
        "pending" -> R.color.warning
        "confirmed" -> R.color.info
        "completed" -> R.color.success
        "cancelled" -> R.color.danger
        else -> R.color.text_muted
    },
)

/** Colour used for stock status badges (ok / low / out). */
fun Context.stockStatusColor(status: String): Int = ContextCompat.getColor(
    this,
    when (status) {
        "ok" -> R.color.success
        "low" -> R.color.warning
        else -> R.color.danger
    },
)

fun stockStatusLabel(status: String): String = when (status) {
    "ok" -> "In stock"
    "low" -> "Low stock"
    else -> "Out of stock"
}

/**
 * Shared failure handling: an expired/invalid token (HTTP 401) signs the user out and returns to the
 * login screen. Returns true when the caller should stop (the user was signed out).
 */
fun Context.handleUnauthorized(failure: ApiResult.Failure): Boolean {
    if (!failure.isUnauthorized) return false
    SessionManager(this).clear()
    toast(failure.message)
    startActivity(Intent(this, LoginActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
    return true
}

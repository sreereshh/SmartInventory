package com.smartinventory.app.data

import com.google.gson.annotations.SerializedName

// Every property has a default so Gson never produces a crash on a missing field.

data class LoginRequest(val username: String, val password: String)

data class User(
    val id: Int = 0,
    val username: String = "",
    val email: String = "",
    @SerializedName("first_name") val firstName: String = "",
    @SerializedName("last_name") val lastName: String = "",
    val role: String = "staff",
    @SerializedName("is_admin") val isAdmin: Boolean = false,
)

data class AuthResponse(val token: String = "", val user: User = User())

/** DRF page wrapper: {"count": 3, "next": null, "previous": null, "results": [...]} */
data class Page<T>(
    val count: Int = 0,
    val next: String? = null,
    val previous: String? = null,
    val results: List<T> = emptyList(),
)

data class Product(
    val id: Int = 0,
    val name: String = "",
    val code: String = "",
    val category: Int = 0,
    @SerializedName("category_name") val categoryName: String = "",
    val description: String = "",
    @SerializedName("purchase_price") val purchasePrice: Double = 0.0,
    @SerializedName("selling_price") val sellingPrice: Double = 0.0,
    val quantity: Int = 0,
    @SerializedName("min_stock_level") val minStockLevel: Int = 0,
    @SerializedName("is_low_stock") val isLowStock: Boolean = false,
    @SerializedName("stock_status") val stockStatus: String = "ok",
)

data class StockLevel(
    val id: Int = 0,
    val name: String = "",
    val code: String = "",
    @SerializedName("category_name") val categoryName: String = "",
    val quantity: Int = 0,
    @SerializedName("min_stock_level") val minStockLevel: Int = 0,
    @SerializedName("stock_status") val stockStatus: String = "ok",
    @SerializedName("stock_value") val stockValue: Double = 0.0,
)

data class Customer(
    val id: Int = 0,
    val name: String = "",
    val phone: String = "",
    val email: String = "",
    val address: String = "",
    @SerializedName("order_count") val orderCount: Int = 0,
)

data class OrderItem(
    val id: Int = 0,
    val product: Int = 0,
    @SerializedName("product_name") val productName: String = "",
    @SerializedName("product_code") val productCode: String = "",
    val quantity: Int = 0,
    @SerializedName("unit_price") val unitPrice: Double = 0.0,
    val subtotal: Double = 0.0,
)

data class Order(
    val id: Int = 0,
    @SerializedName("order_number") val orderNumber: String = "",
    val customer: Int = 0,
    @SerializedName("customer_name") val customerName: String = "",
    val status: String = "pending",
    @SerializedName("status_display") val statusDisplay: String = "Pending",
    @SerializedName("total_amount") val totalAmount: Double = 0.0,
    val notes: String = "",
    @SerializedName("created_by_name") val createdByName: String? = null,
    @SerializedName("created_at") val createdAt: String = "",
    val items: List<OrderItem> = emptyList(),
    @SerializedName("low_stock_alerts") val lowStockAlerts: List<LowStockAlert> = emptyList(),
) {
    companion object {
        const val STATUS_PENDING = "pending"
        const val STATUS_CONFIRMED = "confirmed"
        const val STATUS_COMPLETED = "completed"
        const val STATUS_CANCELLED = "cancelled"
    }
}

data class LowStockAlert(
    val id: Int = 0,
    val name: String = "",
    val quantity: Int = 0,
    @SerializedName("min_stock_level") val minStockLevel: Int = 0,
)

data class OrderLineRequest(val product: Int, val quantity: Int)

data class CreateOrderRequest(val customer: Int, val notes: String, val items: List<OrderLineRequest>)

data class StatusRequest(val status: String)

// ---------------------------------------------------------------- dashboard
data class Dashboard(
    @SerializedName("total_products") val totalProducts: Int = 0,
    @SerializedName("total_customers") val totalCustomers: Int = 0,
    @SerializedName("total_orders") val totalOrders: Int = 0,
    @SerializedName("total_sales") val totalSales: Double = 0.0,
    @SerializedName("low_stock_count") val lowStockCount: Int = 0,
    @SerializedName("out_of_stock_count") val outOfStockCount: Int = 0,
    val sales: DashboardSales = DashboardSales(),
    val inventory: DashboardInventory = DashboardInventory(),
    @SerializedName("recent_orders") val recentOrders: List<RecentOrder> = emptyList(),
    @SerializedName("low_stock_products") val lowStockProducts: List<LowStockProduct> = emptyList(),
)

data class DashboardSales(
    val today: Double = 0.0,
    @SerializedName("today_orders") val todayOrders: Int = 0,
    @SerializedName("this_month") val thisMonth: Double = 0.0,
    @SerializedName("this_month_orders") val thisMonthOrders: Int = 0,
    @SerializedName("gross_profit") val grossProfit: Double = 0.0,
    @SerializedName("average_order_value") val averageOrderValue: Double = 0.0,
    @SerializedName("units_sold") val unitsSold: Int = 0,
)

data class DashboardInventory(
    @SerializedName("total_units") val totalUnits: Int = 0,
    @SerializedName("cost_value") val costValue: Double = 0.0,
    @SerializedName("retail_value") val retailValue: Double = 0.0,
)

data class RecentOrder(
    val id: Int = 0,
    @SerializedName("order_number") val orderNumber: String = "",
    val customer: String = "",
    val status: String = "pending",
    @SerializedName("status_display") val statusDisplay: String = "Pending",
    @SerializedName("total_amount") val totalAmount: Double = 0.0,
    @SerializedName("created_at") val createdAt: String = "",
)

data class LowStockProduct(
    val id: Int = 0,
    val name: String = "",
    val code: String = "",
    val quantity: Int = 0,
    @SerializedName("min_stock_level") val minStockLevel: Int = 0,
    @SerializedName("stock_status") val stockStatus: String = "low",
)

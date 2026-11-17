package com.smartinventory.app.ui

import android.content.Intent
import androidx.recyclerview.widget.RecyclerView
import com.smartinventory.app.R
import com.smartinventory.app.data.ApiClient
import com.smartinventory.app.data.ApiResult
import com.smartinventory.app.data.Order

class ProductsFragment : BaseListFragment() {
    private val adapter = ProductAdapter()
    override val searchHint: String get() = getString(R.string.search_products)
    override val emptyText = "No products yet."

    override fun setupList(recycler: RecyclerView) {
        recycler.adapter = adapter
    }

    override suspend fun fetch(query: String, filter: String): ApiResult<Int> {
        val api = ApiClient.service(requireContext())
        return when (val r = ApiClient.safeCall { api.products(search = query.ifBlank { null }) }) {
            is ApiResult.Success -> {
                adapter.submit(r.data.results)
                ApiResult.Success(r.data.results.size)
            }
            is ApiResult.Failure -> r
        }
    }
}

class StockFragment : BaseListFragment() {
    private val adapter = StockAdapter()
    override val searchHint: String get() = getString(R.string.search_stock)
    override val emptyText = "No products match this filter."
    override val filters = listOf("All" to "", "Low stock" to "low", "Out of stock" to "out", "In stock" to "ok")

    override fun setupList(recycler: RecyclerView) {
        recycler.adapter = adapter
    }

    override suspend fun fetch(query: String, filter: String): ApiResult<Int> {
        val api = ApiClient.service(requireContext())
        return when (val r = ApiClient.safeCall { api.stock(search = query.ifBlank { null }, status = filter.ifBlank { null }) }) {
            is ApiResult.Success -> {
                adapter.submit(
                    r.data.results.map {
                        StockRow(it.name, it.code, it.categoryName, it.quantity, it.minStockLevel, it.stockStatus, it.stockValue)
                    },
                )
                ApiResult.Success(r.data.results.size)
            }
            is ApiResult.Failure -> r
        }
    }
}

class CustomersFragment : BaseListFragment() {
    private val adapter = CustomerAdapter()
    override val searchHint: String get() = getString(R.string.search_customers)
    override val emptyText = "No customers yet."

    override fun setupList(recycler: RecyclerView) {
        recycler.adapter = adapter
    }

    override suspend fun fetch(query: String, filter: String): ApiResult<Int> {
        val api = ApiClient.service(requireContext())
        return when (val r = ApiClient.safeCall { api.customers(search = query.ifBlank { null }) }) {
            is ApiResult.Success -> {
                adapter.submit(r.data.results)
                ApiResult.Success(r.data.results.size)
            }
            is ApiResult.Failure -> r
        }
    }
}

class OrdersFragment : BaseListFragment() {
    private val adapter = OrderAdapter { row ->
        startActivity(Intent(requireContext(), OrderDetailActivity::class.java).putExtra(OrderDetailActivity.EXTRA_ORDER_ID, row.id))
    }
    override val searchHint: String get() = getString(R.string.search_orders)
    override val emptyText = "No orders yet. Tap “New order” to create one."
    override val fabLabel: String get() = getString(R.string.new_order)
    override val filters = listOf(
        "All" to "",
        "Pending" to Order.STATUS_PENDING,
        "Confirmed" to Order.STATUS_CONFIRMED,
        "Completed" to Order.STATUS_COMPLETED,
        "Cancelled" to Order.STATUS_CANCELLED,
    )

    override fun setupList(recycler: RecyclerView) {
        recycler.adapter = adapter
    }

    override fun onFabClick() {
        startActivity(Intent(requireContext(), CreateOrderActivity::class.java))
    }

    override suspend fun fetch(query: String, filter: String): ApiResult<Int> {
        val api = ApiClient.service(requireContext())
        return when (val r = ApiClient.safeCall { api.orders(search = query.ifBlank { null }, status = filter.ifBlank { null }) }) {
            is ApiResult.Success -> {
                adapter.submit(
                    r.data.results.map {
                        OrderRow(it.id, it.orderNumber, it.customerName, it.status, it.statusDisplay, it.totalAmount, it.createdAt)
                    },
                )
                ApiResult.Success(r.data.results.size)
            }
            is ApiResult.Failure -> r
        }
    }
}

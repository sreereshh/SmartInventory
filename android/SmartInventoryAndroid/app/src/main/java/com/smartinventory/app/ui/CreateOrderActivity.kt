package com.smartinventory.app.ui

import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.smartinventory.app.data.ApiClient
import com.smartinventory.app.data.ApiResult
import com.smartinventory.app.data.CreateOrderRequest
import com.smartinventory.app.data.Customer
import com.smartinventory.app.data.OrderLineRequest
import com.smartinventory.app.data.Product
import com.smartinventory.app.databinding.ActivityCreateOrderBinding
import com.smartinventory.app.util.formatMoney
import com.smartinventory.app.util.handleUnauthorized
import com.smartinventory.app.util.toast
import kotlinx.coroutines.launch

/**
 * Create an order: pick a customer, add one or more products with quantities, see the grand total
 * and submit to POST /api/orders/. The server reduces the stock in one database transaction and
 * rejects the order when stock is insufficient.
 */
class CreateOrderActivity : AppCompatActivity() {

    private lateinit var binding: ActivityCreateOrderBinding
    private var customers: List<Customer> = emptyList()
    private var products: List<Product> = emptyList()
    private val lines = mutableListOf<OrderLine>()
    private val lineAdapter = OrderLineAdapter { line ->
        lines.remove(line)
        refreshLines()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCreateOrderBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.rvLines.layoutManager = LinearLayoutManager(this)
        binding.rvLines.adapter = lineAdapter
        binding.btnAddLine.setOnClickListener { addLine() }
        binding.btnPlace.setOnClickListener { placeOrder() }
        binding.btnRetry.setOnClickListener { loadData() }
        refreshLines()
        loadData()
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    private fun loadData() {
        binding.progress.visibility = View.VISIBLE
        binding.messageBox.visibility = View.GONE
        lifecycleScope.launch {
            val api = ApiClient.service(this@CreateOrderActivity)
            val customerResult = ApiClient.safeCall { api.customers() }
            val productResult = ApiClient.safeCall { api.products() }
            binding.progress.visibility = View.GONE

            val failure = (customerResult as? ApiResult.Failure) ?: (productResult as? ApiResult.Failure)
            if (failure != null) {
                if (handleUnauthorized(failure)) return@launch
                showMessage(failure.message, retry = true)
                return@launch
            }
            customers = (customerResult as ApiResult.Success).data.results
            // Only products that can actually be sold are offered.
            products = (productResult as ApiResult.Success).data.results.filter { it.quantity > 0 }

            if (customers.isEmpty()) {
                showMessage("There are no customers yet. Add a customer on the website first.", retry = false)
                return@launch
            }
            if (products.isEmpty()) {
                showMessage("No products are in stock. Add stock on the website first.", retry = false)
                return@launch
            }
            binding.spinnerCustomer.adapter = ArrayAdapter(
                this@CreateOrderActivity, android.R.layout.simple_spinner_dropdown_item,
                customers.map { "${it.name}  (${it.phone})" },
            )
            binding.spinnerProduct.adapter = ArrayAdapter(
                this@CreateOrderActivity, android.R.layout.simple_spinner_dropdown_item,
                products.map { "${it.name} (${it.code}) • stock ${it.quantity} • ${formatMoney(it.sellingPrice)}" },
            )
        }
    }

    private fun showMessage(text: String, retry: Boolean) {
        binding.tvMessage.text = text
        binding.btnRetry.visibility = if (retry) View.VISIBLE else View.GONE
        binding.messageBox.visibility = View.VISIBLE
    }

    private fun addLine() {
        if (products.isEmpty()) return
        val product = products[binding.spinnerProduct.selectedItemPosition]
        val qty = binding.etQuantity.text?.toString()?.trim()?.toIntOrNull()
        if (qty == null || qty < 1) {
            toast("Enter a quantity of 1 or more.")
            return
        }
        val existing = lines.firstOrNull { it.product.id == product.id }
        val newQty = (existing?.quantity ?: 0) + qty
        if (newQty > product.quantity) {
            toast("Only ${product.quantity} unit(s) of ${product.name} in stock.")
            return
        }
        if (existing != null) existing.quantity = newQty else lines.add(OrderLine(product, qty))
        binding.etQuantity.setText("1")
        refreshLines()
    }

    private fun refreshLines() {
        lineAdapter.submit(lines.toList())
        binding.tvNoItems.visibility = if (lines.isEmpty()) View.VISIBLE else View.GONE
        binding.tvTotal.text = formatMoney(lines.sumOf { it.subtotal })
    }

    private fun placeOrder() {
        if (customers.isEmpty() || products.isEmpty()) {
            toast("Customers and products are not loaded yet.")
            return
        }
        if (lines.isEmpty()) {
            toast("Add at least one product to the order.")
            return
        }
        val customer = customers[binding.spinnerCustomer.selectedItemPosition]
        val request = CreateOrderRequest(
            customer = customer.id,
            notes = binding.etNotes.text?.toString()?.trim().orEmpty(),
            items = lines.map { OrderLineRequest(it.product.id, it.quantity) },
        )

        setBusy(true)
        lifecycleScope.launch {
            val api = ApiClient.service(this@CreateOrderActivity)
            when (val result = ApiClient.safeCall { api.createOrder(request) }) {
                is ApiResult.Success -> {
                    val order = result.data
                    val message = "Order ${order.orderNumber} placed. Total ${formatMoney(order.totalAmount)}."
                    if (order.lowStockAlerts.isEmpty()) {
                        toast(message)
                        finish()
                    } else {
                        val alerts = order.lowStockAlerts.joinToString("\n") {
                            "• ${it.name}: ${it.quantity} left (minimum ${it.minStockLevel})"
                        }
                        AlertDialog.Builder(this@CreateOrderActivity)
                            .setTitle("Order placed – low stock alert")
                            .setMessage("$message\n\n$alerts")
                            .setPositiveButton("OK") { _, _ -> finish() }
                            .setCancelable(false)
                            .show()
                    }
                }
                is ApiResult.Failure -> {
                    setBusy(false)
                    if (handleUnauthorized(result)) return@launch
                    AlertDialog.Builder(this@CreateOrderActivity)
                        .setTitle("Order not placed")
                        .setMessage(result.message)
                        .setPositiveButton("OK", null)
                        .show()
                    // Stock may have changed – refresh the product list silently.
                    refreshProductsQuietly()
                }
            }
        }
    }

    private fun refreshProductsQuietly() {
        lifecycleScope.launch {
            val api = ApiClient.service(this@CreateOrderActivity)
            val result = ApiClient.safeCall { api.products() }
            if (result is ApiResult.Success) {
                products = result.data.results.filter { it.quantity > 0 }
                val selected = binding.spinnerProduct.selectedItemPosition
                binding.spinnerProduct.adapter = ArrayAdapter(
                    this@CreateOrderActivity, android.R.layout.simple_spinner_dropdown_item,
                    products.map { "${it.name} (${it.code}) • stock ${it.quantity} • ${formatMoney(it.sellingPrice)}" },
                )
                if (selected in products.indices) binding.spinnerProduct.setSelection(selected)
                // Drop lines that no longer fit the real stock.
                lines.clear()
                refreshLines()
            }
        }
    }

    private fun setBusy(busy: Boolean) {
        binding.btnPlace.isEnabled = !busy
        binding.btnAddLine.isEnabled = !busy
        binding.progress.visibility = if (busy) View.VISIBLE else View.GONE
    }
}

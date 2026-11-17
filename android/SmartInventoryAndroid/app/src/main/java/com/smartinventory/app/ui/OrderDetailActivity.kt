package com.smartinventory.app.ui

import android.content.res.ColorStateList
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.smartinventory.app.data.ApiClient
import com.smartinventory.app.data.ApiResult
import com.smartinventory.app.data.Order
import com.smartinventory.app.data.StatusRequest
import com.smartinventory.app.databinding.ActivityOrderDetailBinding
import com.smartinventory.app.databinding.ItemOrderItemBinding
import com.smartinventory.app.util.formatDate
import com.smartinventory.app.util.formatMoney
import com.smartinventory.app.util.handleUnauthorized
import com.smartinventory.app.util.orderStatusColor
import com.smartinventory.app.util.toast
import kotlinx.coroutines.launch

/** Order details with status actions (confirm → complete, or cancel which restores stock). */
class OrderDetailActivity : AppCompatActivity() {

    private lateinit var binding: ActivityOrderDetailBinding
    private var orderId = 0
    private var currentOrder: Order? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityOrderDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Order"

        orderId = intent.getIntExtra(EXTRA_ORDER_ID, 0)
        if (orderId == 0) {
            toast("Order not found.")
            finish()
            return
        }
        binding.btnRetry.setOnClickListener { load() }
        binding.btnNext.setOnClickListener {
            when (currentOrder?.status) {
                Order.STATUS_PENDING -> changeStatus(Order.STATUS_CONFIRMED)
                Order.STATUS_CONFIRMED -> changeStatus(Order.STATUS_COMPLETED)
            }
        }
        binding.btnCancelOrder.setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle("Cancel this order?")
                .setMessage("The ordered quantities will be added back to stock. This cannot be undone.")
                .setPositiveButton("Cancel order") { _, _ -> changeStatus(Order.STATUS_CANCELLED) }
                .setNegativeButton("Keep order", null)
                .show()
        }
        load()
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    private fun load() {
        binding.progress.visibility = View.VISIBLE
        binding.messageBox.visibility = View.GONE
        lifecycleScope.launch {
            val api = ApiClient.service(this@OrderDetailActivity)
            val result = ApiClient.safeCall { api.order(orderId) }
            binding.progress.visibility = View.GONE
            when (result) {
                is ApiResult.Success -> render(result.data)
                is ApiResult.Failure -> {
                    if (handleUnauthorized(result)) return@launch
                    binding.content.visibility = View.GONE
                    binding.tvMessage.text = result.message
                    binding.messageBox.visibility = View.VISIBLE
                }
            }
        }
    }

    private fun changeStatus(newStatus: String) {
        setBusy(true)
        lifecycleScope.launch {
            val api = ApiClient.service(this@OrderDetailActivity)
            val result = ApiClient.safeCall { api.setOrderStatus(orderId, StatusRequest(newStatus)) }
            setBusy(false)
            when (result) {
                is ApiResult.Success -> {
                    toast(
                        if (newStatus == Order.STATUS_CANCELLED) "Order cancelled and stock restored."
                        else "Order marked as ${result.data.statusDisplay}.",
                    )
                    render(result.data)
                }
                is ApiResult.Failure -> {
                    if (handleUnauthorized(result)) return@launch
                    toast(result.message)
                }
            }
        }
    }

    private fun setBusy(busy: Boolean) {
        binding.btnNext.isEnabled = !busy
        binding.btnCancelOrder.isEnabled = !busy
        binding.progress.visibility = if (busy) View.VISIBLE else View.GONE
    }

    private fun render(order: Order) = with(binding) {
        currentOrder = order
        supportActionBar?.title = order.orderNumber
        content.visibility = View.VISIBLE
        tvCustomer.text = order.customerName
        tvBadge.text = order.statusDisplay
        tvBadge.backgroundTintList = ColorStateList.valueOf(this@OrderDetailActivity.orderStatusColor(order.status))
        tvMeta.text = "Placed ${formatDate(order.createdAt)}" + (order.createdByName?.let { " by $it" } ?: "")
        tvNotes.text = "Notes: ${order.notes}"
        tvNotes.visibility = if (order.notes.isBlank()) View.GONE else View.VISIBLE
        tvTotal.text = formatMoney(order.totalAmount)

        itemsContainer.removeAllViews()
        for (item in order.items) {
            val row = ItemOrderItemBinding.inflate(LayoutInflater.from(this@OrderDetailActivity), itemsContainer, false)
            row.tvName.text = item.productName
            row.tvDetail.text = "${item.productCode}  •  ${item.quantity} × ${formatMoney(item.unitPrice)}"
            row.tvSubtotal.text = formatMoney(item.subtotal)
            itemsContainer.addView(row.root)
        }

        val nextLabel = when (order.status) {
            Order.STATUS_PENDING -> "Confirm order"
            Order.STATUS_CONFIRMED -> "Mark completed"
            else -> null
        }
        btnNext.visibility = if (nextLabel == null) View.GONE else View.VISIBLE
        btnNext.text = nextLabel ?: ""
        btnCancelOrder.visibility =
            if (order.status == Order.STATUS_PENDING || order.status == Order.STATUS_CONFIRMED) View.VISIBLE else View.GONE
    }

    companion object {
        const val EXTRA_ORDER_ID = "order_id"
    }
}

package com.smartinventory.app.ui

import android.content.res.ColorStateList
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.smartinventory.app.data.Customer
import com.smartinventory.app.data.Product
import com.smartinventory.app.databinding.ItemCustomerBinding
import com.smartinventory.app.databinding.ItemOrderBinding
import com.smartinventory.app.databinding.ItemOrderLineBinding
import com.smartinventory.app.databinding.ItemProductBinding
import com.smartinventory.app.databinding.ItemStockBinding
import com.smartinventory.app.util.formatDate
import com.smartinventory.app.util.formatMoney
import com.smartinventory.app.util.orderStatusColor
import com.smartinventory.app.util.stockStatusColor
import com.smartinventory.app.util.stockStatusLabel

/** UI models shared by several screens (the dashboard and the list endpoints return slightly different JSON). */
data class StockRow(
    val name: String,
    val code: String,
    val category: String,
    val quantity: Int,
    val minLevel: Int,
    val status: String,
    val value: Double?,
)

data class OrderRow(
    val id: Int,
    val number: String,
    val customer: String,
    val status: String,
    val statusDisplay: String,
    val total: Double,
    val createdAt: String,
)

data class OrderLine(val product: Product, var quantity: Int) {
    val subtotal: Double get() = product.sellingPrice * quantity
}

abstract class SimpleAdapter<T, B : androidx.viewbinding.ViewBinding> : RecyclerView.Adapter<SimpleAdapter.VH<B>>() {
    protected var items: List<T> = emptyList()

    fun submit(list: List<T>) {
        items = list
        notifyDataSetChanged()
    }

    class VH<B : androidx.viewbinding.ViewBinding>(val binding: B) : RecyclerView.ViewHolder(binding.root)

    protected abstract fun inflate(inflater: LayoutInflater, parent: ViewGroup): B
    protected abstract fun bind(binding: B, item: T)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH<B> =
        VH(inflate(LayoutInflater.from(parent.context), parent))

    override fun onBindViewHolder(holder: VH<B>, position: Int) = bind(holder.binding, items[position])

    override fun getItemCount(): Int = items.size
}

class ProductAdapter : SimpleAdapter<Product, ItemProductBinding>() {
    override fun inflate(inflater: LayoutInflater, parent: ViewGroup) = ItemProductBinding.inflate(inflater, parent, false)

    override fun bind(binding: ItemProductBinding, item: Product) = with(binding) {
        tvName.text = item.name
        tvPrice.text = formatMoney(item.sellingPrice)
        tvMeta.text = "${item.code}  •  ${item.categoryName}"
        tvQty.text = "In stock: ${item.quantity}  (min ${item.minStockLevel})"
        tvBadge.text = stockStatusLabel(item.stockStatus)
        tvBadge.backgroundTintList = ColorStateList.valueOf(root.context.stockStatusColor(item.stockStatus))
    }
}

class StockAdapter : SimpleAdapter<StockRow, ItemStockBinding>() {
    override fun inflate(inflater: LayoutInflater, parent: ViewGroup) = ItemStockBinding.inflate(inflater, parent, false)

    override fun bind(binding: ItemStockBinding, item: StockRow) = with(binding) {
        tvName.text = item.name
        tvPrice.text = item.value?.let { formatMoney(it) } ?: ""
        tvMeta.text = if (item.category.isBlank()) item.code else "${item.code}  •  ${item.category}"
        tvQty.text = "Quantity: ${item.quantity}  (min ${item.minLevel})"
        tvBadge.text = stockStatusLabel(item.status)
        tvBadge.backgroundTintList = ColorStateList.valueOf(root.context.stockStatusColor(item.status))
    }
}

class CustomerAdapter : SimpleAdapter<Customer, ItemCustomerBinding>() {
    override fun inflate(inflater: LayoutInflater, parent: ViewGroup) = ItemCustomerBinding.inflate(inflater, parent, false)

    override fun bind(binding: ItemCustomerBinding, item: Customer) = with(binding) {
        tvName.text = item.name
        tvPhone.text = item.phone
        tvEmail.text = item.email
        tvEmail.visibility = if (item.email.isBlank()) android.view.View.GONE else android.view.View.VISIBLE
        tvAddress.text = item.address
        tvAddress.visibility = if (item.address.isBlank()) android.view.View.GONE else android.view.View.VISIBLE
        tvOrders.text = "${item.orderCount} order(s)"
    }
}

class OrderAdapter(private val onClick: (OrderRow) -> Unit) : SimpleAdapter<OrderRow, ItemOrderBinding>() {
    override fun inflate(inflater: LayoutInflater, parent: ViewGroup) = ItemOrderBinding.inflate(inflater, parent, false)

    override fun bind(binding: ItemOrderBinding, item: OrderRow) = with(binding) {
        tvNumber.text = item.number
        tvCustomer.text = item.customer
        tvDate.text = formatDate(item.createdAt)
        tvTotal.text = formatMoney(item.total)
        tvBadge.text = item.statusDisplay
        tvBadge.backgroundTintList = ColorStateList.valueOf(root.context.orderStatusColor(item.status))
        root.setOnClickListener { onClick(item) }
    }
}

class OrderLineAdapter(private val onRemove: (OrderLine) -> Unit) : SimpleAdapter<OrderLine, ItemOrderLineBinding>() {
    override fun inflate(inflater: LayoutInflater, parent: ViewGroup) = ItemOrderLineBinding.inflate(inflater, parent, false)

    override fun bind(binding: ItemOrderLineBinding, item: OrderLine) = with(binding) {
        tvName.text = item.product.name
        tvDetail.text = "${item.quantity} × ${formatMoney(item.product.sellingPrice)}  (stock ${item.product.quantity})"
        tvSubtotal.text = formatMoney(item.subtotal)
        btnRemove.setOnClickListener { onRemove(item) }
    }
}

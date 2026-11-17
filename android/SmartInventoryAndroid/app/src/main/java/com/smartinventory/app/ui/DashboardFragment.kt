package com.smartinventory.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.smartinventory.app.R
import com.smartinventory.app.data.ApiClient
import com.smartinventory.app.data.ApiResult
import com.smartinventory.app.data.Dashboard
import com.smartinventory.app.databinding.FragmentDashboardBinding
import com.smartinventory.app.util.formatMoney
import com.smartinventory.app.util.handleUnauthorized
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

/** Dashboard: every number comes from GET /api/dashboard/ (live database values). */
class DashboardFragment : Fragment() {

    private var _binding: FragmentDashboardBinding? = null
    private val binding get() = _binding!!
    private var loadJob: Job? = null
    private var firstLoadDone = false

    private val lowStockAdapter = StockAdapter()
    private val recentAdapter = OrderAdapter { row ->
        startActivity(Intent(requireContext(), OrderDetailActivity::class.java).putExtra(OrderDetailActivity.EXTRA_ORDER_ID, row.id))
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentDashboardBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        binding.rvLowStock.layoutManager = LinearLayoutManager(requireContext())
        binding.rvLowStock.adapter = lowStockAdapter
        binding.rvRecent.layoutManager = LinearLayoutManager(requireContext())
        binding.rvRecent.adapter = recentAdapter
        binding.swipe.setColorSchemeResources(R.color.primary)
        binding.swipe.setOnRefreshListener { load(showSpinner = false) }
        binding.btnRetry.setOnClickListener { load(showSpinner = true) }
    }

    override fun onResume() {
        super.onResume()
        load(showSpinner = !firstLoadDone)
    }

    private fun load(showSpinner: Boolean) {
        if (_binding == null) return
        loadJob?.cancel()
        loadJob = viewLifecycleOwner.lifecycleScope.launch {
            if (showSpinner) {
                binding.progress.visibility = View.VISIBLE
                binding.messageBox.visibility = View.GONE
            }
            val api = ApiClient.service(requireContext())
            val result = ApiClient.safeCall { api.dashboard() }
            binding.progress.visibility = View.GONE
            binding.swipe.isRefreshing = false
            when (result) {
                is ApiResult.Success -> {
                    firstLoadDone = true
                    binding.messageBox.visibility = View.GONE
                    binding.swipe.visibility = View.VISIBLE
                    render(result.data)
                }
                is ApiResult.Failure -> {
                    if (requireContext().handleUnauthorized(result)) return@launch
                    if (!firstLoadDone) {
                        binding.swipe.visibility = View.GONE
                        binding.tvMessage.text = result.message
                        binding.messageBox.visibility = View.VISIBLE
                    } else {
                        // keep showing the old numbers; tell the user the refresh failed
                        android.widget.Toast.makeText(requireContext(), result.message, android.widget.Toast.LENGTH_LONG).show()
                    }
                }
            }
        }
    }

    private fun render(d: Dashboard) = with(binding) {
        tvTotalProducts.text = d.totalProducts.toString()
        tvTotalCustomers.text = d.totalCustomers.toString()
        tvTotalOrders.text = d.totalOrders.toString()
        tvTotalSales.text = formatMoney(d.totalSales)
        tvToday.text = formatMoney(d.sales.today)
        tvMonth.text = formatMoney(d.sales.thisMonth)
        tvInventoryValue.text = formatMoney(d.inventory.costValue)
        tvLowCount.text = d.lowStockCount.toString()

        lowStockAdapter.submit(
            d.lowStockProducts.map { StockRow(it.name, it.code, "", it.quantity, it.minStockLevel, it.stockStatus, null) },
        )
        tvLowEmpty.visibility = if (d.lowStockProducts.isEmpty()) View.VISIBLE else View.GONE

        recentAdapter.submit(
            d.recentOrders.map { OrderRow(it.id, it.orderNumber, it.customer, it.status, it.statusDisplay, it.totalAmount, it.createdAt) },
        )
        tvRecentEmpty.visibility = if (d.recentOrders.isEmpty()) View.VISIBLE else View.GONE
    }

    override fun onDestroyView() {
        loadJob?.cancel()
        _binding = null
        super.onDestroyView()
    }
}

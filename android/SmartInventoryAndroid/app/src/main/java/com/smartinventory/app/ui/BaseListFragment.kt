package com.smartinventory.app.ui

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.chip.Chip
import com.smartinventory.app.R
import com.smartinventory.app.data.ApiResult
import com.smartinventory.app.databinding.FragmentListBinding
import com.smartinventory.app.util.handleUnauthorized
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

/**
 * Shared behaviour for the Products / Stock / Customers / Orders tabs:
 * search box (debounced), optional filter chips, pull-to-refresh, loading indicator,
 * empty state and an error state with a Retry button.
 */
abstract class BaseListFragment : Fragment() {

    private var _binding: FragmentListBinding? = null
    protected val binding get() = _binding!!

    /** Hint of the search box; null hides the search box. */
    protected abstract val searchHint: String?
    protected open val filters: List<Pair<String, String>> = emptyList()
    protected open val emptyText: String = "Nothing to show."
    protected open val fabLabel: String? = null

    protected abstract fun setupList(recycler: RecyclerView)

    /** Fetches data, updates the adapter and returns the number of rows (or the failure). */
    protected abstract suspend fun fetch(query: String, filter: String): ApiResult<Int>

    protected open fun onFabClick() {}

    private var query = ""
    private var filter = ""
    private var loadJob: Job? = null
    private var firstLoadDone = false
    private val handler = Handler(Looper.getMainLooper())
    private var pendingSearch: Runnable? = null

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentListBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        binding.recycler.layoutManager = LinearLayoutManager(requireContext())
        setupList(binding.recycler)

        binding.swipe.setColorSchemeResources(R.color.primary)
        binding.swipe.setOnRefreshListener { reload(showSpinner = false) }
        binding.btnRetry.setOnClickListener { reload(showSpinner = true) }

        val hint = searchHint
        if (hint == null) {
            binding.searchLayout.visibility = View.GONE
        } else {
            binding.searchLayout.hint = hint
            binding.etSearch.addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
                override fun afterTextChanged(s: Editable?) {
                    pendingSearch?.let { handler.removeCallbacks(it) }
                    val text = s?.toString()?.trim().orEmpty()
                    pendingSearch = Runnable {
                        if (text != query) {
                            query = text
                            reload(showSpinner = false)
                        }
                    }.also { handler.postDelayed(it, 400) }
                }
            })
        }

        if (filters.isNotEmpty()) {
            binding.chipScroll.visibility = View.VISIBLE
            val valueById = HashMap<Int, String>()
            filters.forEachIndexed { index, (label, value) ->
                val chip = layoutInflater.inflate(R.layout.chip_filter, binding.chipGroup, false) as Chip
                chip.id = View.generateViewId()
                chip.text = label
                chip.isChecked = index == 0
                valueById[chip.id] = value
                binding.chipGroup.addView(chip)
            }
            filter = filters.first().second
            binding.chipGroup.setOnCheckedStateChangeListener { _, checkedIds ->
                val selected = valueById[checkedIds.firstOrNull()] ?: ""
                if (selected != filter) {
                    filter = selected
                    reload(showSpinner = true)
                }
            }
        }

        val label = fabLabel
        if (label != null) {
            binding.fab.text = label
            binding.fab.visibility = View.VISIBLE
            binding.fab.setOnClickListener { onFabClick() }
        }
    }

    override fun onResume() {
        super.onResume()
        // Refresh every time the tab becomes visible (e.g. after creating an order).
        reload(showSpinner = !firstLoadDone)
    }

    protected fun reload(showSpinner: Boolean) {
        if (_binding == null) return
        loadJob?.cancel()
        loadJob = viewLifecycleOwner.lifecycleScope.launch {
            if (showSpinner) {
                binding.progress.visibility = View.VISIBLE
                binding.messageBox.visibility = View.GONE
            }
            val result = fetch(query, filter)
            binding.progress.visibility = View.GONE
            binding.swipe.isRefreshing = false
            when (result) {
                is ApiResult.Success -> {
                    firstLoadDone = true
                    if (result.data == 0) {
                        showMessage(if (query.isNotEmpty()) "No results for \"$query\"." else emptyText, retry = false)
                    } else {
                        binding.messageBox.visibility = View.GONE
                    }
                }
                is ApiResult.Failure -> {
                    if (requireContext().handleUnauthorized(result)) return@launch
                    showMessage(result.message, retry = true)
                }
            }
        }
    }

    private fun showMessage(text: String, retry: Boolean) {
        binding.tvMessage.text = text
        binding.btnRetry.visibility = if (retry) View.VISIBLE else View.GONE
        binding.messageBox.visibility = View.VISIBLE
    }

    override fun onDestroyView() {
        pendingSearch?.let { handler.removeCallbacks(it) }
        loadJob?.cancel()
        binding.recycler.adapter = null
        _binding = null
        super.onDestroyView()
    }
}

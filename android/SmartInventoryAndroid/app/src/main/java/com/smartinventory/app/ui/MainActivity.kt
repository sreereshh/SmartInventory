package com.smartinventory.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.smartinventory.app.R
import com.smartinventory.app.data.ApiClient
import com.smartinventory.app.data.SessionManager
import com.smartinventory.app.databinding.ActivityMainBinding
import kotlinx.coroutines.launch

/** Hosts the five tabs (Dashboard, Products, Stock, Customers, Orders) behind a bottom navigation bar. */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        session = SessionManager(this)
        if (!session.isLoggedIn) {
            goToLogin()
            return
        }
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.subtitle = "${session.username} (${session.role})"

        binding.bottomNav.setOnItemSelectedListener { item ->
            show(item.itemId)
            true
        }
        if (savedInstanceState == null) {
            binding.bottomNav.selectedItemId = R.id.nav_dashboard
        } else {
            updateTitle(binding.bottomNav.selectedItemId)
        }
    }

    private fun show(itemId: Int) {
        val fragment: Fragment = when (itemId) {
            R.id.nav_products -> ProductsFragment()
            R.id.nav_stock -> StockFragment()
            R.id.nav_customers -> CustomersFragment()
            R.id.nav_orders -> OrdersFragment()
            else -> DashboardFragment()
        }
        updateTitle(itemId)
        supportFragmentManager.beginTransaction().replace(R.id.fragment_container, fragment).commit()
    }

    private fun updateTitle(itemId: Int) {
        supportActionBar?.title = getString(
            when (itemId) {
                R.id.nav_products -> R.string.nav_products
                R.id.nav_stock -> R.string.nav_stock
                R.id.nav_customers -> R.string.nav_customers
                R.id.nav_orders -> R.string.nav_orders
                else -> R.string.nav_dashboard
            },
        )
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == R.id.action_logout) {
            AlertDialog.Builder(this)
                .setTitle(R.string.logout)
                .setMessage("Sign out of ${session.username}?")
                .setPositiveButton(R.string.logout) { _, _ -> logout() }
                .setNegativeButton(R.string.cancel, null)
                .show()
            return true
        }
        return super.onOptionsItemSelected(item)
    }

    private fun logout() {
        lifecycleScope.launch {
            // Best effort: tell the server to delete the token, then always clear it locally.
            val api = ApiClient.service(this@MainActivity)
            ApiClient.safeCall { api.logout() }
            session.clear()
            goToLogin()
        }
    }

    private fun goToLogin() {
        startActivity(Intent(this, LoginActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
        finish()
    }
}

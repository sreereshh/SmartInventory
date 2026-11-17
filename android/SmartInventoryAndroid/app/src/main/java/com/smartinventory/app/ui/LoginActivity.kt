package com.smartinventory.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.inputmethod.EditorInfo
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.smartinventory.app.data.ApiClient
import com.smartinventory.app.data.ApiResult
import com.smartinventory.app.data.LoginRequest
import com.smartinventory.app.data.SessionManager
import com.smartinventory.app.databinding.ActivityLoginBinding
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        session = SessionManager(this)
        if (session.isLoggedIn) {
            openMain()
            return
        }
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

      
        binding.btnLogin.setOnClickListener { attemptLogin() }
        binding.etPassword.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                attemptLogin()
                true
            } else {
                false
            }
        }
    }

    private fun attemptLogin() {
        val username = binding.etUsername.text?.toString()?.trim().orEmpty()
        val password = binding.etPassword.text?.toString().orEmpty()
        if (username.isEmpty() || password.isEmpty()) {
            showError("Enter your username and password.")
            return
        }
        

        setLoading(true)
        lifecycleScope.launch {
            val api = ApiClient.service(this@LoginActivity)
            when (val result = ApiClient.safeCall { api.login(LoginRequest(username, password)) }) {
                is ApiResult.Success -> {
                    session.saveLogin(result.data)
                    openMain()
                }
                is ApiResult.Failure -> {
                    setLoading(false)
                    showError(result.message)
                }
            }
        }
    }

    private fun setLoading(loading: Boolean) {
        binding.progress.visibility = if (loading) View.VISIBLE else View.GONE
        binding.btnLogin.isEnabled = !loading
        binding.btnLogin.text = if (loading) "" else getString(com.smartinventory.app.R.string.sign_in)
        if (loading) binding.tvError.visibility = View.GONE
    }

    private fun showError(message: String) {
        binding.tvError.text = message
        binding.tvError.visibility = View.VISIBLE
    }

    private fun openMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}

package com.smartinventory.app.data

import android.content.Context
import com.google.gson.Gson
import com.google.gson.JsonParser
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.IOException
import java.net.SocketTimeoutException
import java.util.concurrent.TimeUnit

/** Result of an API call: either data or a human readable error. */
sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Failure(val message: String, val code: Int = 0) : ApiResult<Nothing>() {
        val isUnauthorized: Boolean get() = code == 401
    }
}

/** Builds the Retrofit client. The token is added to every request as `Authorization: Token <key>`. */
object ApiClient {

    private var cachedUrl: String? = null
    private var cachedService: ApiService? = null

    @Synchronized
    fun service(context: Context): ApiService {
        val session = SessionManager(context)
        val url = session.baseUrl
        cachedService?.let { if (cachedUrl == url) return it }

        val authInterceptor = Interceptor { chain ->
            val builder = chain.request().newBuilder().header("Accept", "application/json")
            session.token?.takeIf { it.isNotBlank() }?.let { builder.header("Authorization", "Token $it") }
            chain.proceed(builder.build())
        }
        val client = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
        val service = Retrofit.Builder()
            .baseUrl(url)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create(Gson()))
            .build()
            .create(ApiService::class.java)
        cachedUrl = url
        cachedService = service
        return service
    }

    /**
     * Runs a Retrofit call and converts every outcome (success, HTTP error, no network, timeout,
     * bad URL) into an [ApiResult]. Never throws.
     */
    suspend fun <T> safeCall(call: suspend () -> Response<T>): ApiResult<T> {
        return try {
            val response = call()
            val body = response.body()
            when {
                response.isSuccessful && body != null -> ApiResult.Success(body)
                response.isSuccessful -> ApiResult.Failure("The server returned an empty response.", response.code())
                else -> ApiResult.Failure(parseError(response), response.code())
            }
        } catch (e: SocketTimeoutException) {
            ApiResult.Failure("The server took too long to respond. Please try again.")
        } catch (e: IOException) {
            ApiResult.Failure("Cannot reach the server. Check your internet connection and the Server URL.")
        } catch (e: IllegalArgumentException) {
            ApiResult.Failure("The Server URL is not valid.")
        } catch (e: Exception) {
            ApiResult.Failure("Unexpected error: ${e.message ?: e.javaClass.simpleName}")
        }
    }

    /** Reads `{"detail": "..."}` from DRF error responses (our API always uses this shape). */
    private fun <T> parseError(response: Response<T>): String {
        val raw = try {
            response.errorBody()?.string()
        } catch (e: Exception) {
            null
        }
        if (!raw.isNullOrBlank()) {
            try {
                val json = JsonParser.parseString(raw)
                if (json.isJsonObject) {
                    val detail = json.asJsonObject.get("detail")
                    if (detail != null && detail.isJsonPrimitive) return detail.asString
                }
            } catch (e: Exception) {
                // fall through to generic messages
            }
        }
        return when (response.code()) {
            401 -> "Your session has expired. Please sign in again."
            403 -> "You do not have permission to do that."
            404 -> "Not found."
            in 500..599 -> "Server error (${response.code()}). Please try again later."
            else -> "Request failed (HTTP ${response.code()})."
        }
    }
}

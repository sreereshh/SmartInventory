package com.smartinventory.app.data

import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/** Mirrors the Django REST API documented at /api/docs/ (Swagger UI). */
interface ApiService {

    @POST("api/auth/login/")
    suspend fun login(@Body body: LoginRequest): Response<AuthResponse>

    @POST("api/auth/logout/")
    suspend fun logout(): Response<ResponseBody>

    @GET("api/dashboard/")
    suspend fun dashboard(): Response<Dashboard>

    @GET("api/products/")
    suspend fun products(
        @Query("search") search: String? = null,
        @Query("page_size") pageSize: Int = PAGE_SIZE,
    ): Response<Page<Product>>

    @GET("api/inventory/stock/")
    suspend fun stock(
        @Query("search") search: String? = null,
        @Query("status") status: String? = null,
        @Query("page_size") pageSize: Int = PAGE_SIZE,
    ): Response<Page<StockLevel>>

    @GET("api/customers/")
    suspend fun customers(
        @Query("search") search: String? = null,
        @Query("page_size") pageSize: Int = PAGE_SIZE,
    ): Response<Page<Customer>>

    @GET("api/orders/")
    suspend fun orders(
        @Query("search") search: String? = null,
        @Query("status") status: String? = null,
        @Query("page_size") pageSize: Int = PAGE_SIZE,
    ): Response<Page<Order>>

    @GET("api/orders/{id}/")
    suspend fun order(@Path("id") id: Int): Response<Order>

    @POST("api/orders/")
    suspend fun createOrder(@Body body: CreateOrderRequest): Response<Order>

    @POST("api/orders/{id}/status/")
    suspend fun setOrderStatus(@Path("id") id: Int, @Body body: StatusRequest): Response<Order>

    companion object {
        /** The API allows up to 200 rows per page. */
        const val PAGE_SIZE = 200
    }
}

from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.stock_list, name="stock_list"),
    path("stock-in/", views.stock_in, name="stock_in"),
    path("stock-out/", views.stock_out, name="stock_out"),
    path("history/", views.stock_history, name="stock_history"),
]

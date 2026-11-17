from django.db.models import Count, F, Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view, inline_serializer
from rest_framework import filters, mixins, serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import parse_date, parse_month
from customers.models import Customer
from inventory.models import StockTransaction
from inventory.services import StockError, apply_stock
from orders.models import Order
from orders.services import OrderError, change_status, create_order
from products.models import Category, Product
from reports import services as report_services

from .permissions import AdminDeletesOnly
from .serializers import (
    CategorySerializer, CustomerSerializer, LoginSerializer, OrderCreateSerializer, OrderSerializer,
    OrderStatusSerializer, ProductSerializer, RegisterSerializer, StockInSerializer, StockLevelSerializer,
    StockOutSerializer, StockTransactionSerializer, UserSerializer,
)

ERROR_SCHEMA = inline_serializer("Error", {"detail": serializers.CharField(), "errors": serializers.DictField(required=False)})
AuthResponse = inline_serializer("AuthResponse", {"token": serializers.CharField(), "user": UserSerializer()})


# ---------------------------------------------------------------------- auth
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(tags=["Authentication"], request=LoginSerializer, responses={200: AuthResponse, 401: ERROR_SCHEMA},
                   summary="Log in and obtain an API token")
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response({"detail": "Invalid username or password.", "errors": serializer.errors},
                            status=status.HTTP_401_UNAUTHORIZED)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(tags=["Authentication"], request=RegisterSerializer, responses={201: AuthResponse, 400: ERROR_SCHEMA},
                   summary="Register a new Staff account")
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Authentication"], request=None,
                   responses={200: inline_serializer("LogoutResponse", {"detail": serializers.CharField()})},
                   summary="Log out (deletes the API token)")
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Logged out."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Authentication"], responses=UserSerializer, summary="Current user")
    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ------------------------------------------------------------- CRUD viewsets
@extend_schema_view(
    list=extend_schema(tags=["Categories"]), retrieve=extend_schema(tags=["Categories"]),
    create=extend_schema(tags=["Categories"]), update=extend_schema(tags=["Categories"]),
    partial_update=extend_schema(tags=["Categories"]),
    destroy=extend_schema(tags=["Categories"], description="Admin only. Fails with 409 if the category has products."),
)
class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [AdminDeletesOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        return Category.objects.annotate(product_count=Count("products"))


@extend_schema_view(
    list=extend_schema(
        tags=["Products"],
        parameters=[
            OpenApiParameter("category", OpenApiTypes.INT, description="Filter by category id"),
            OpenApiParameter("status", OpenApiTypes.STR, enum=["low", "out", "ok"], description="Filter by stock status"),
        ],
    ),
    retrieve=extend_schema(tags=["Products"]),
    create=extend_schema(tags=["Products"], description="`quantity` is the opening stock and is logged as a stock transaction."),
    update=extend_schema(tags=["Products"]), partial_update=extend_schema(tags=["Products"]),
    destroy=extend_schema(tags=["Products"], description="Admin only. Fails with 409 if the product was ordered."),
)
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [AdminDeletesOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code", "description", "category__name"]
    ordering_fields = ["name", "code", "quantity", "selling_price", "created_at"]

    def get_queryset(self):
        qs = Product.objects.select_related("category")
        params = self.request.query_params
        if params.get("category", "").isdigit():
            qs = qs.filter(category_id=int(params["category"]))
        stock = params.get("status")
        if stock == "low":
            qs = qs.filter(quantity__lte=F("min_stock_level"), quantity__gt=0)
        elif stock == "out":
            qs = qs.filter(quantity=0)
        elif stock == "ok":
            qs = qs.filter(quantity__gt=F("min_stock_level"))
        elif params.get("low_stock", "").lower() in ("1", "true", "yes"):
            qs = qs.filter(quantity__lte=F("min_stock_level"))
        return qs


@extend_schema_view(
    list=extend_schema(tags=["Customers"]), retrieve=extend_schema(tags=["Customers"]),
    create=extend_schema(tags=["Customers"]), update=extend_schema(tags=["Customers"]),
    partial_update=extend_schema(tags=["Customers"]),
    destroy=extend_schema(tags=["Customers"], description="Admin only. Fails with 409 if the customer has orders."),
)
class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [AdminDeletesOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "phone", "email", "address"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        return Customer.objects.annotate(order_count=Count("orders"))


# ----------------------------------------------------------------- inventory
@extend_schema(
    tags=["Inventory"], summary="Current stock levels",
    parameters=[
        OpenApiParameter("status", OpenApiTypes.STR, enum=["low", "out", "ok"], description="low includes only items above 0"),
        OpenApiParameter("category", OpenApiTypes.INT),
    ],
)
class StockLevelView(ListAPIView):
    serializer_class = StockLevelSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code", "category__name"]
    ordering_fields = ["name", "quantity"]
    forced_status = None

    def get_queryset(self):
        qs = Product.objects.select_related("category").order_by("name")
        params = self.request.query_params
        if params.get("category", "").isdigit():
            qs = qs.filter(category_id=int(params["category"]))
        stock = self.forced_status or params.get("status")
        if stock == "low":
            qs = qs.filter(quantity__lte=F("min_stock_level"), quantity__gt=0)
        elif stock == "out":
            qs = qs.filter(quantity=0)
        elif stock == "ok":
            qs = qs.filter(quantity__gt=F("min_stock_level"))
        elif stock == "alert":  # low + out
            qs = qs.filter(quantity__lte=F("min_stock_level"))
        return qs


@extend_schema(tags=["Inventory"], summary="Low-stock notifications (low and out-of-stock products)")
class LowStockView(StockLevelView):
    forced_status = "alert"


@extend_schema(
    tags=["Inventory"], summary="Stock history",
    parameters=[
        OpenApiParameter("product", OpenApiTypes.INT), OpenApiParameter("type", OpenApiTypes.STR, enum=["IN", "OUT"]),
    ],
)
class StockTransactionListView(ListAPIView):
    serializer_class = StockTransactionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["product__name", "product__code", "note"]

    def get_queryset(self):
        qs = StockTransaction.objects.select_related("product", "order", "created_by")
        params = self.request.query_params
        if params.get("product", "").isdigit():
            qs = qs.filter(product_id=int(params["product"]))
        if params.get("type") in StockTransaction.Type.values:
            qs = qs.filter(transaction_type=params["type"])
        return qs


class _StockMovementView(APIView):
    transaction_type = None
    serializer_class = None

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            txn = apply_stock(
                product_id=data["product"].pk, quantity=data["quantity"],
                transaction_type=self.transaction_type, reason=data["reason"],
                note=data.get("note", ""), user=request.user,
            )
        except StockError as exc:
            return Response({"detail": str(exc), "errors": {"quantity": [str(exc)]}}, status=status.HTTP_400_BAD_REQUEST)
        product = txn.product
        return Response(
            {
                "transaction": StockTransactionSerializer(txn).data,
                "current_quantity": product.quantity,
                "low_stock_alert": product.is_low_stock,
            },
            status=status.HTTP_201_CREATED,
        )


STOCK_RESPONSE = inline_serializer(
    "StockMovementResponse",
    {"transaction": StockTransactionSerializer(), "current_quantity": serializers.IntegerField(),
     "low_stock_alert": serializers.BooleanField()},
)


@extend_schema(tags=["Inventory"], summary="Stock in (add stock)", request=StockInSerializer,
               responses={201: STOCK_RESPONSE, 400: ERROR_SCHEMA})
class StockInView(_StockMovementView):
    transaction_type = StockTransaction.Type.IN
    serializer_class = StockInSerializer


@extend_schema(tags=["Inventory"], summary="Stock out (remove stock)", request=StockOutSerializer,
               description="Returns 400 if the quantity exceeds available stock (negative stock is impossible).",
               responses={201: STOCK_RESPONSE, 400: ERROR_SCHEMA})
class StockOutView(_StockMovementView):
    transaction_type = StockTransaction.Type.OUT
    serializer_class = StockOutSerializer


# -------------------------------------------------------------------- orders
@extend_schema_view(
    list=extend_schema(
        tags=["Orders"],
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, enum=Order.Status.values),
            OpenApiParameter("customer", OpenApiTypes.INT),
            OpenApiParameter("date_from", OpenApiTypes.DATE), OpenApiParameter("date_to", OpenApiTypes.DATE),
        ],
    ),
    retrieve=extend_schema(tags=["Orders"]),
    create=extend_schema(
        tags=["Orders"], request=OrderCreateSerializer, responses={201: OrderSerializer, 400: ERROR_SCHEMA},
        description="Creates an order and reduces stock in one database transaction. "
                    "Returns 400 (nothing saved) if any product has insufficient stock.",
    ),
)
class OrderViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["order_number", "customer__name", "customer__phone"]
    ordering_fields = ["created_at", "total_amount"]

    def get_serializer_class(self):
        return OrderCreateSerializer if self.action == "create" else OrderSerializer

    def get_queryset(self):
        qs = Order.objects.select_related("customer", "created_by").prefetch_related("items__product")
        params = self.request.query_params
        if params.get("status") in Order.Status.values:
            qs = qs.filter(status=params["status"])
        if params.get("customer", "").isdigit():
            qs = qs.filter(customer_id=int(params["customer"]))
        date_from, date_to = parse_date(params.get("date_from")), parse_date(params.get("date_to"))
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        items = [{"product": line["product"].pk, "quantity": line["quantity"]} for line in data["items"]]
        try:
            order, low_stock = create_order(customer=data["customer"], items=items, user=request.user, notes=data["notes"])
        except OrderError as exc:
            return Response({"detail": " ".join(exc.errors), "errors": {"items": exc.errors}},
                            status=status.HTTP_400_BAD_REQUEST)
        order = self.get_queryset().get(pk=order.pk)
        body = OrderSerializer(order).data
        body["low_stock_alerts"] = [
            {"id": p.pk, "name": p.name, "quantity": p.quantity, "min_stock_level": p.min_stock_level}
            for p in low_stock
        ]
        return Response(body, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Orders"], request=OrderStatusSerializer, responses={200: OrderSerializer, 400: ERROR_SCHEMA},
        summary="Change order status",
        description="Allowed: pending→confirmed|cancelled, confirmed→completed|cancelled. "
                    "Cancelling restores stock automatically.",
    )
    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            change_status(order.pk, serializer.validated_data["status"], user=request.user)
        except OrderError as exc:
            return Response({"detail": " ".join(exc.errors), "errors": {"status": exc.errors}},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(self.get_queryset().get(pk=order.pk)).data)


# ----------------------------------------------------------------- dashboard
@extend_schema(tags=["Dashboard"], summary="Dashboard statistics (live from the database)",
               responses=inline_serializer("Dashboard", {"total_products": serializers.IntegerField(),
                                                         "total_customers": serializers.IntegerField(),
                                                         "total_orders": serializers.IntegerField(),
                                                         "total_sales": serializers.FloatField(),
                                                         "low_stock_count": serializers.IntegerField(),
                                                         "sales": serializers.DictField(),
                                                         "inventory": serializers.DictField(),
                                                         "recent_orders": serializers.ListField(child=serializers.DictField()),
                                                         "low_stock_products": serializers.ListField(child=serializers.DictField())}))
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(report_services.dashboard_data())


# ------------------------------------------------------------------- reports
class _ReportView(APIView):
    permission_classes = [IsAuthenticated]


@extend_schema(tags=["Reports"], summary="Daily sales report",
               parameters=[OpenApiParameter("date", OpenApiTypes.DATE, description="YYYY-MM-DD (default: today)")],
               responses=OpenApiTypes.OBJECT)
class DailyReportView(_ReportView):
    def get(self, request):
        raw = request.query_params.get("date")
        day = parse_date(raw, None if raw else timezone.localdate())
        if day is None:
            return Response({"detail": "Invalid date. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(report_services.daily_report(day))


@extend_schema(tags=["Reports"], summary="Monthly sales report",
               parameters=[OpenApiParameter("month", OpenApiTypes.STR, description="YYYY-MM (default: this month)")],
               responses=OpenApiTypes.OBJECT)
class MonthlyReportView(_ReportView):
    def get(self, request):
        raw = request.query_params.get("month")
        today = timezone.localdate()
        parsed = parse_month(raw, None if raw else (today.year, today.month))
        if parsed is None:
            return Response({"detail": "Invalid month. Use YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(report_services.monthly_report(*parsed))


@extend_schema(tags=["Reports"], summary="Total sales report (all time)", responses=OpenApiTypes.OBJECT)
class TotalSalesReportView(_ReportView):
    def get(self, request):
        return Response(report_services.total_sales_report())


@extend_schema(tags=["Reports"], summary="Inventory report",
               parameters=[OpenApiParameter("category", OpenApiTypes.INT)], responses=OpenApiTypes.OBJECT)
class InventoryReportView(_ReportView):
    def get(self, request):
        category = request.query_params.get("category", "")
        return Response(report_services.inventory_report(int(category) if category.isdigit() else None))


@extend_schema(tags=["Reports"], summary="Low stock report", responses=OpenApiTypes.OBJECT)
class LowStockReportView(_ReportView):
    def get(self, request):
        return Response(report_services.low_stock_report())


@extend_schema(tags=["Reports"], summary="Order report",
               parameters=[OpenApiParameter("date_from", OpenApiTypes.DATE), OpenApiParameter("date_to", OpenApiTypes.DATE),
                           OpenApiParameter("status", OpenApiTypes.STR, enum=Order.Status.values),
                           OpenApiParameter("customer", OpenApiTypes.INT)],
               responses=OpenApiTypes.OBJECT)
class OrderReportView(_ReportView):
    def get(self, request):
        p = request.query_params
        for key in ("date_from", "date_to"):
            if p.get(key) and parse_date(p[key]) is None:
                return Response({"detail": f"Invalid {key}. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            report_services.order_report(
                parse_date(p.get("date_from")), parse_date(p.get("date_to")), p.get("status"),
                int(p["customer"]) if p.get("customer", "").isdigit() else None,
            )
        )

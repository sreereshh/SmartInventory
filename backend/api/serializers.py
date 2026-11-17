from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from accounts.models import User
from customers.models import Customer
from inventory.models import StockTransaction
from inventory.services import create_product_with_opening_stock
from orders.models import Order, OrderItem
from products.models import Category, Product


# ------------------------------------------------------------------- auth
class UserSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(source="is_admin_role", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "is_admin"]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"), username=attrs["username"], password=attrs["password"]
        )
        if user is None or not user.is_active:
            raise serializers.ValidationError("Invalid username or password.", code="authentication")
        attrs["user"] = user
        return attrs


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password"]

    def validate(self, attrs):
        candidate = User(username=attrs.get("username", ""), email=attrs.get("email", ""))
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        # Public sign-up always creates a Staff account.
        return User.objects.create_user(role=User.Role.STAFF, **validated_data)


# --------------------------------------------------------------- catalogue
class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "description", "product_count", "created_at"]
        read_only_fields = ["created_at"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "code", "category", "category_name", "description",
            "purchase_price", "selling_price", "quantity", "min_stock_level",
            "is_low_stock", "stock_status", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {
            "code": {"validators": []},  # uniqueness is checked case-insensitively below
            "quantity": {"required": False, "min_value": 0},
        }

    def validate_code(self, value):
        value = value.strip().upper()
        qs = Product.objects.filter(code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A product with this code already exists.")
        return value

    def validate(self, attrs):
        purchase = attrs.get("purchase_price", getattr(self.instance, "purchase_price", None))
        selling = attrs.get("selling_price", getattr(self.instance, "selling_price", None))
        if purchase is not None and selling is not None and selling < purchase:
            raise serializers.ValidationError(
                {"selling_price": "Selling price is lower than purchase price."}
            )
        if self.instance is not None and "quantity" in attrs and attrs["quantity"] != self.instance.quantity:
            raise serializers.ValidationError(
                {"quantity": "Quantity cannot be edited directly. Use /api/inventory/stock-in/ or /stock-out/."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        quantity = validated_data.pop("quantity", 0)
        product = Product(**validated_data)
        return create_product_with_opening_stock(product, quantity, self.context["request"].user)

    def update(self, instance, validated_data):
        validated_data.pop("quantity", None)
        return super().update(instance, validated_data)


class CustomerSerializer(serializers.ModelSerializer):
    order_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "name", "phone", "email", "address", "order_count", "created_at"]
        read_only_fields = ["created_at"]


# --------------------------------------------------------------- inventory
class StockTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    type_display = serializers.CharField(source="get_transaction_type_display", read_only=True)
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True, default=None)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)

    class Meta:
        model = StockTransaction
        fields = [
            "id", "product", "product_name", "product_code", "transaction_type", "type_display",
            "reason", "reason_display", "quantity", "quantity_before", "quantity_after",
            "order", "order_number", "note", "created_by_name", "created_at",
        ]
        read_only_fields = fields


class StockLevelSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    stock_value = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "code", "category_name", "quantity", "min_stock_level",
            "stock_status", "is_low_stock", "stock_value",
        ]
        read_only_fields = fields


class _StockMovementBase(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")


class StockInSerializer(_StockMovementBase):
    reason = serializers.ChoiceField(
        choices=[
            StockTransaction.Reason.PURCHASE, StockTransaction.Reason.RETURN,
            StockTransaction.Reason.ADJUSTMENT, StockTransaction.Reason.OTHER,
        ],
        default=StockTransaction.Reason.PURCHASE,
    )


class StockOutSerializer(_StockMovementBase):
    reason = serializers.ChoiceField(
        choices=[
            StockTransaction.Reason.DAMAGE, StockTransaction.Reason.ADJUSTMENT, StockTransaction.Reason.OTHER,
        ],
        default=StockTransaction.Reason.DAMAGE,
    )


# ------------------------------------------------------------------ orders
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "product_code", "quantity", "unit_price", "subtotal"]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "customer", "customer_name", "status", "status_display",
            "total_amount", "notes", "created_by_name", "created_at", "updated_at", "items",
        ]
        read_only_fields = fields


class OrderLineInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = OrderLineInputSerializer(many=True, allow_empty=False)

    def validate_items(self, items):
        seen = set()
        for line in items:
            pid = line["product"].pk
            if pid in seen:
                raise serializers.ValidationError("Each product may appear only once per order.")
            seen.add(pid)
        return items


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)

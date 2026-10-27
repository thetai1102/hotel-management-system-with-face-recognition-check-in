from django.contrib import messages
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from accounts.decorators import group_required

from .forms import CustomerForm
from .models import Customer


# ============================================================
# CUSTOMER LIST
# DANH SÁCH KHÁCH HÀNG
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def customer_list(request):
    """
    Display and search staff-managed customers.
    Hiển thị và tìm kiếm customer do staff quản lý.
    """

    search_query = (
        request.GET.get(
            "q",
            ""
        ).strip()
    )

    customers = (
        Customer.objects
        .all()
        .order_by(
            "-created_at"
        )
    )

    if search_query:
        customers = customers.filter(
            Q(
                full_name__icontains=search_query
            )
            | Q(
                phone__icontains=search_query
            )
            | Q(
                email__icontains=search_query
            )
            | Q(
                id_card_number__icontains=search_query
            )
        )

    return render(
        request,
        "customers/customer_list.html",
        {
            "customers": customers,
            "search_query": search_query,
        },
    )


# ============================================================
# CREATE CUSTOMER
# TẠO KHÁCH HÀNG
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def customer_create(request):
    """
    Create a staff-managed customer record.
    Tạo customer do staff quản lý.
    """

    if request.method == "POST":

        form = CustomerForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            customer = form.save()

            messages.success(
                request,
                "Customer created successfully.",
            )

            return redirect(
                "customer_detail",
                pk=customer.pk,
            )

    else:

        form = CustomerForm()

    return render(
        request,
        "customers/customer_form.html",
        {
            "form": form,
            "title": "Add Customer",
        },
    )


# ============================================================
# CUSTOMER DETAIL
# CHI TIẾT KHÁCH HÀNG
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def customer_detail(
    request,
    pk,
):
    """
    Display customer details.
    Hiển thị chi tiết customer.
    """

    customer = get_object_or_404(
        Customer,
        pk=pk,
    )

    return render(
        request,
        "customers/customer_detail.html",
        {
            "customer": customer,
        },
    )


# ============================================================
# UPDATE CUSTOMER
# CẬP NHẬT KHÁCH HÀNG
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def customer_update(
    request,
    pk,
):
    """
    Update customer information.
    Cập nhật thông tin customer.
    """

    customer = get_object_or_404(
        Customer,
        pk=pk,
    )

    if request.method == "POST":

        form = CustomerForm(
            request.POST,
            request.FILES,
            instance=customer,
        )

        if form.is_valid():

            updated_customer = form.save()

            messages.success(
                request,
                "Customer updated successfully.",
            )

            return redirect(
                "customer_detail",
                pk=updated_customer.pk,
            )

    else:

        form = CustomerForm(
            instance=customer
        )

    return render(
        request,
        "customers/customer_form.html",
        {
            "form": form,
            "title": "Edit Customer",
        },
    )


# ============================================================
# DELETE CUSTOMER
# XÓA KHÁCH HÀNG
# ============================================================

@group_required(
    "Admin",
    "Receptionist",
)
def customer_delete(
    request,
    pk,
):
    """
    Delete a customer only when no protected history exists.
    Chỉ xóa customer khi không có lịch sử được PROTECT bảo vệ.
    """

    customer = get_object_or_404(
        Customer,
        pk=pk,
    )

    if request.method == "POST":

        try:
            customer.delete()

        except ProtectedError:
            # Booking and CheckIn history must remain intact.
            # Lịch sử Booking và CheckIn phải được bảo toàn.
            messages.error(
                request,
                "This customer cannot be deleted because "
                "they already have protected booking or "
                "check-in history.",
            )

            return redirect(
                "customer_detail",
                pk=customer.pk,
            )

        messages.success(
            request,
            "Customer deleted successfully.",
        )

        return redirect(
            "customer_list"
        )

    return render(
        request,
        "customers/customer_confirm_delete.html",
        {
            "customer": customer,
        },
    )
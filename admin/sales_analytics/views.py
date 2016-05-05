from django.shortcuts import render
from admin.sales_analytics import keen


def dashboard(request):
    return render(request, 'sales_analytics/dashboard.html', keen.KEEN_CREDENTIALS)


def user_session(request):
    return render(request, 'sales_analytics/user_session.html', keen.KEEN_CREDENTIALS)


def products_view(request):
    return render(request, 'sales_analytics/products_view.html', keen.KEEN_CREDENTIALS)


def products_usage(request):
    return render(request, 'sales_analytics/products_usage.html', keen.KEEN_CREDENTIALS)


def debug_test(request):
    return render(request, 'sales_analytics/debug_test.html', keen.KEEN_CREDENTIALS)

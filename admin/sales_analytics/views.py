from django.shortcuts import render
from admin.sales_analytics import keen
from admin.sales_analytics.metrics import user_count, multi_product_metrics_yearly, multi_product_metrics_monthly


def dashboard(request):

    context = keen.KEEN_CREDENTIALS.copy()
    context.update({
        'user_count': user_count,
        'multi_product_metrics_yearly': multi_product_metrics_yearly,
        'multi_product_metrics_monthly': multi_product_metrics_monthly,
    })
    return render(request, 'sales_analytics/dashboard.html', context)


def user_session(request):
    return render(request, 'sales_analytics/user_session.html', keen.KEEN_CREDENTIALS)


def product_view(request):
    return render(request, 'sales_analytics/product_view.html', keen.KEEN_CREDENTIALS)

def product_usage(request):
    return render(request, 'sales_analytics/product_usage.html', keen.KEEN_CREDENTIALS)


def debug_test(request):
    return render(request, 'sales_analytics/debug_test.html', keen.KEEN_CREDENTIALS)

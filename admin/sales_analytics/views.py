from django.shortcuts import render
from admin.base.settings import KEEN_PROJECT_ID, KEEN_READ_KEY

KEEN_CREDENTIALS = {
    'keen_project_id': KEEN_PROJECT_ID,
    'keen_read_key': KEEN_READ_KEY
}


def dashboard(request):
    return render(request, 'sales_analytics/dashboard.html', KEEN_CREDENTIALS)


def user_session(request):
    return render(request, 'sales_analytics/user_session.html', KEEN_CREDENTIALS)


def product_usage(request):
    return render(request, 'sales_analytics/product_usage.html', KEEN_CREDENTIALS)

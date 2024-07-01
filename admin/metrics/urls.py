from django.urls import re_path
from django.contrib.auth.decorators import login_required as login

from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', login(views.MetricsView.as_view()), name='metrics'),
]

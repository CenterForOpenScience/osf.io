from django.conf.urls import url
from django.contrib.auth.decorators import login_required as login

from . import views

urlpatterns = [
    url(r'^$', login(views.MetricsView.as_view()), name='metrics'),
]

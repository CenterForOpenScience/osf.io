from django.conf.urls import include, url

app_name = 'admin'

urlpatterns = [
    url(r'^settings/', include('admin.project_limit_number.setting.urls', namespace='settings')),
    url(r'^templates/', include('admin.project_limit_number.template.urls', namespace='templates')),
]

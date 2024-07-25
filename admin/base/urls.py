from django.conf.urls import include
from django.urls import re_path
from django.contrib import admin
from admin.base.settings import ADMIN_BASE, DEBUG
from admin.base import views

base_pattern = f'^{ADMIN_BASE}'

urlpatterns = [
    ### ADMIN ###
    re_path(
        base_pattern,
        include([
            re_path(r'^$', views.home, name='home'),
            re_path(r'^admin/', admin.site.urls),
            re_path(r'^provider_asset_files/', include('admin.provider_asset_files.urls', namespace='provider_asset_files')),
            re_path(r'^institution_asset_files/', include('admin.institution_asset_files.urls', namespace='institution_asset_files')),
            re_path(r'^banners/', include('admin.banners.urls', namespace='banners')),
            re_path(r'^brands/', include('admin.brands.urls', namespace='brands')),
            re_path(r'^comments/', include('admin.comments.urls', namespace='comments')),
            re_path(r'^institutions/', include('admin.institutions.urls', namespace='institutions')),
            re_path(r'^preprint_providers/', include('admin.preprint_providers.urls', namespace='preprint_providers')),
            re_path(r'^collection_providers/', include('admin.collection_providers.urls', namespace='collection_providers')),
            re_path(r'^registration_providers/', include('admin.registration_providers.urls', namespace='registration_providers')),
            re_path(r'^account/', include('admin.common_auth.urls', namespace='auth')),
            re_path(r'^nodes/', include('admin.nodes.urls', namespace='nodes')),
            re_path(r'^preprints/', include('admin.preprints.urls', namespace='preprints')),
            re_path(r'^subjects/', include('admin.subjects.urls', namespace='subjects')),
            re_path(r'^users/', include('admin.users.urls', namespace='users')),
            re_path(r'^maintenance/', include('admin.maintenance.urls', namespace='maintenance')),
            re_path(r'^meetings/', include('admin.meetings.urls', namespace='meetings')),
            re_path(r'^metrics/', include('admin.metrics.urls', namespace='metrics')),
            re_path(r'^osf_groups/', include('admin.osf_groups.urls', namespace='osf_groups')),
            re_path(r'^management/', include('admin.management.urls', namespace='management')),
            re_path(r'^internet_archive/', include('admin.internet_archive.urls', namespace='internet_archive')),
            re_path(r'^schema_responses/', include('admin.schema_responses.urls', namespace='schema_responses')),
            re_path(r'^registration_schemas/', include('admin.registration_schemas.urls', namespace='registration_schemas')),
            re_path(r'^cedar_metadata_templates/', include('admin.cedar.urls', namespace='cedar_metadata_templates')),
        ]),
    ),
]

if DEBUG:
    import debug_toolbar

    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]

admin.site.site_header = 'OSF-Admin administration'

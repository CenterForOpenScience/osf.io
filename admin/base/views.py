from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import DetailView
from django.views.defaults import page_not_found

from admin.base.utils import get_unprotected_url_patterns, osf_staff_check


@user_passes_test(osf_staff_check)
def home(request):
    context = {}
    return render(request, 'home.html', context)


@user_passes_test(osf_staff_check)
def unprotected_views(request):
    context = {'unprotected_url_patterns': get_unprotected_url_patterns()}
    return render(request, 'unprotected_views.html', context)


def admin_auth_middleware_check(request):
    # This view is used to check and see if the AdminLoginRequiredMiddleware is working correctly.
    # It requires no permissions so that, if unauthenticated users can access it, the middleware is not working correctly.
    return HttpResponse('AdminLoginRequiredMiddleware check: you are signed in as a staff user.')


class GuidView(DetailView):
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return page_not_found(
                request,
                AttributeError(f'resource with id "{kwargs.get("guid") or kwargs.get("id")}" not found.')
            )

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.views.generic import DetailView
from django.views.defaults import page_not_found

from admin.base.utils import osf_staff_check


@user_passes_test(osf_staff_check)
def home(request):
    context = {}
    return render(request, 'home.html', context)


class GuidView(DetailView):
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return page_not_found(
                request,
                AttributeError(f'resource with id "{kwargs.get("guid") or kwargs.get("id")}" not found.')
            )

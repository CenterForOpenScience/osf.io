from django.shortcuts import render
from django.views.generic import ListView, TemplateView
from django.contrib import messages
from django.shortcuts import redirect
from admin.desk.utils import DeskClient, DeskError, DeskCustomerNotFound
from admin.users.views import UserMixin


class DeskCaseList(UserMixin, ListView):
    template_name = 'desk/cases.html'
    ordering = 'updated_at'
    paginate_by = 100
    paginate_orphans = 5
    permission_required = 'osf.view_desk'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except DeskError as e:
            return render(
                request,
                'desk/desk_error.html',
                context={
                    'error': e.message,
                    'status': e.status_code,
                    'content': e.content,
                },
                status=e.status_code
            )

    def get_queryset(self):
        customer = self.get_object()
        email = customer.emails.values_list('address', flat=True).first()
        return DeskClient(self.request.user).cases({'email': email})

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            user_id=self.kwargs['guid'],
            desk_case=f'https://{DeskClient.SITE_NAME}.desk.com/web/agent/case/',
            desk_customer=f'https://{DeskClient.SITE_NAME}.desk.com/web/agent/customer/',
            **kwargs
        )


class DeskCustomer(UserMixin, TemplateView):
    template_name = 'desk/customer.html'
    permission_required = 'osf.view_desk'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except DeskCustomerNotFound as e:
            return render(
                request,
                'desk/user_not_found.html',
                context={
                    'message': e.message,
                    'desk_inbox': f'https://{DeskClient.SITE_NAME}.desk.com/web/agent/filters/inbox'
                },
                status=404
            )
        except DeskError as e:
            return render(
                request, 'desk/desk_error.html',
                context={
                    'error': e.message,
                    'status': e.status_code,
                    'content': e.content,
                },
                status=e.status_code
            )
        except PermissionError as e:
            return render(
                request, 'desk/desk_error.html',
                context={
                    'error': 'Permission Error',
                    'content': e,
                },
                status=500
            )

    def get_object(self, queryset=None):
        customer = super().get_object()
        email = customer.emails.values_list('address', flat=True).first()
        return DeskClient(self.request.user).find_customer({'email': email})

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            customer_info=self.get_object(),
            desk_customer=f'https://{DeskClient.SITE_NAME}.desk.com/web/agent/customer/',
            **kwargs
        )

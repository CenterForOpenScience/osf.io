from django.shortcuts import render
from django.views.generic import ListView, DetailView

from website.project.model import User

from admin.base.utils import OSFAdmin
from admin.desk.utils import DeskClient, DeskError


class DeskCaseList(OSFAdmin, ListView):
    template_name = 'desk/cases.html'
    ordering = 'updated_at'
    context_object_name = 'cases'
    paginate_by = 100
    paginate_orphans = 5

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(DeskCaseList, self).dispatch(request, *args, **kwargs)
        except DeskError as e:
            return render(request, 'desk/desk_error.html',
                          context={
                              'error': e.message,
                              'status': e.status_code,
                              'content': e.content,
                          })

    def get_queryset(self):
        customer_id = self.kwargs.get('user_id', None)
        customer = User.load(customer_id)
        email = customer.emails[0]
        desk = DeskClient(self.request.user)
        params = {
            'status': 'new,open,closed',
            'email': email,
        }
        queryset = desk.cases(params)
        return queryset

    def get_context_data(self, **kwargs):
        kwargs.setdefault('user_id', self.kwargs.get('user_id'))
        kwargs.setdefault('desk_case', 'https://{}.desk.com/web/agent/case/'.format(DeskClient.SITE_NAME))
        kwargs.setdefault('desk_customer', 'https://{}.desk.com/web/agent/customer/'.format(DeskClient.SITE_NAME))
        return super(DeskCaseList, self).get_context_data(**kwargs)


class DeskCustomer(OSFAdmin, DetailView):
    template_name = 'desk/customer.html'
    context_object_name = 'customer'

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(DeskCustomer, self).dispatch(request, *args, **kwargs)
        except AttributeError as e:
            return render(request, 'desk/user_not_found.html',
                          context={
                              'email': e.message,
                              'desk_inbox': 'https://{}.desk.com/web/agent/filters/inbox'.format(DeskClient.SITE_NAME)
                          })
        except DeskError as e:
            return render(request, 'desk/desk_error.html',
                          context={
                              'error': e.message,
                              'status': e.status_code,
                              'content': e.content,
                          })

    def get_object(self, queryset=None):
        customer_id = self.kwargs.get('user_id', None)
        customer = User.load(customer_id)
        email = customer.emails[0]
        desk = DeskClient(self.request.user)
        params = {'email': email}
        customer = desk.find_customer(params)
        if customer == {}:
            raise AttributeError(email)
        return customer

    def get_context_data(self, **kwargs):
        kwargs.setdefault('user_id', self.kwargs.get('user_id'))
        kwargs.setdefault('desk_link', 'https://{}.desk.com/web/agent/customer/'.format(DeskClient.SITE_NAME))
        return super(DeskCustomer, self).get_context_data(**kwargs)

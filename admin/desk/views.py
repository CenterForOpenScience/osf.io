from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.views.defaults import page_not_found

from website.project.model import User

from .utils import DeskClient, DeskError


class DeskCaseList(ListView):
    template_name = 'desk/cases.html'
    ordering = 'updated_at'
    context_object_name = 'cases'
    paginate_by = 10
    paginate_orphans = 1

    def get_queryset(self):
        user = self.request.user
        desk = DeskClient(username=user.desk_email,
                          password=user.desk_password)
        params = {
            'status': 'new,open,closed',
            'email': 'michael@cos.io',
        }
        queryset = desk.cases(params)
        return queryset


class DeskCustomer(DetailView):
    template_name = 'desk/customer.html'
    context_object_name = 'customer'

    def get(self, request, *args, **kwargs):
        try:
            return super(DeskCustomer, self).get(request, *args, **kwargs)
        except (AttributeError, DeskError) as e:
            return render(request, 'desk/user_not_found.html',
                          context={'email': e.status})

    def get_object(self, queryset=None):
        customer_id = self.kwargs.get('user_id', None)
        customer = User.load(customer_id)
        email = customer.emails[0]
        user = self.request.user
        desk = DeskClient(username=user.desk_email,
                          password=user.desk_password)
        params = {'email': email}
        customer = desk.find_customer(params)
        if customer == {}:
            raise DeskError(email)
        return customer

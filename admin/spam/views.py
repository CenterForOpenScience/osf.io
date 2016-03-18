from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.generic import FormView, ListView
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.views.defaults import page_not_found

from modularodm import Q
from website.project.model import Comment

from .serializers import serialize_comment
from .forms import ConfirmForm


class SpamList(ListView):
    template_name = 'spam/spam_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = 'date_created'
    context_object_name = 'spam'

    def get_queryset(self):
        query = (
            Q('reports', 'ne', {}) &
            Q('reports', 'ne', None) &
            Q('spam_status', 'eq', int(self.request.GET.get('status', u'1')))
        )
        return Comment.find(query).sort(self.ordering)

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(queryset)
        paginator, page, queryset, is_paginated = self.paginate_queryset(
            queryset, page_size)
        kwargs.setdefault('spam', map(serialize_comment, queryset))
        kwargs.setdefault('page', page)
        kwargs.setdefault('status', self.request.GET.get('status', u'1'))
        kwargs.setdefault('page_number', page.number)
        return super(SpamList, self).get_context_data(**kwargs)


class UserSpamList(SpamList):
    template_name = 'spam/user.html'

    def get_queryset(self):
        query = (
            Q('reports', 'ne', {}) &
            Q('reports', 'ne', None) &
            Q('user', 'eq', self.kwargs.get('user_id', None)) &
            Q('spam_status', 'eq', int(self.request.GET.get('status', u'1')))
        )
        return Comment.find(query).sort(self.ordering)

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(queryset)
        paginator, page, queryset, is_paginated = self.paginate_queryset(
            queryset, page_size)
        kwargs.setdefault('spam', map(serialize_comment, queryset))
        kwargs.setdefault('page', page)
        kwargs.setdefault('status', self.request.GET.get('status', u'1'))
        kwargs.setdefault('page_number', page.number)
        kwargs.setdefault('user_id', self.kwargs.get('user_id', None))
        return super(UserSpamList, self).get_context_data(**kwargs)


class SpamDetail(FormView):
    form_class = ConfirmForm
    template_name = 'spam/detail.html'
    spam_id = None
    page = 1

    def __init__(self):
        self.item = None
        super(SpamDetail, self).__init__()

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context_data(**kwargs)
        except AttributeError:
            return page_not_found(request)  # TODO: 1.9 update to have exception with node/user 404.html will be added
        self.page = request.GET.get('page', 1)
        context['page_number'] = self.page
        context['form'] = self.get_form()
        return self.render_to_response(context)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        try:
            context = self.get_context_data(**kwargs)
        except AttributeError:
            return page_not_found(request)  # TODO: 1.9 update to have exception
        self.page = request.GET.get('page', 1)
        context['page_number'] = self.page
        context['form'] = self.get_form()
        if context['form'].is_valid():
            return self.form_valid(context['form'])
        else:
            return render(request, self.template_name, context=context)
        # return super(SpamDetail, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        self.item = Comment.load(self.kwargs.get('spam_id', None))
        kwargs = super(SpamDetail, self).get_context_data(**kwargs)
        kwargs.setdefault('page_number', self.request.GET.get('page', 1))
        kwargs.setdefault('comment', serialize_comment(self.item))
        kwargs.setdefault('status', self.request.GET.get('status', u'1'))
        return kwargs

    def form_valid(self, form):
        if int(form.cleaned_data.get('confirm')) == Comment.SPAM:
            self.item.confirm_spam(save=True)
        else:
            self.item.confirm_ham(save=True)
        return super(SpamDetail, self).form_valid(form)

    @property
    def success_url(self):
        return '{}?page={}&status={}'.format(
            reverse('spam:detail', kwargs={'spam_id': self.spam_id}),
            self.request.GET.get('page', 1),
            self.request.GET.get('status', u'1')
        )


@login_required
def email(request, spam_id):
    context = {
        'comment': serialize_comment(Comment.load(spam_id), full=True),
        'page_number': request.GET.get('page', 1),
    }
    return render(request, 'spam/email.html', context)

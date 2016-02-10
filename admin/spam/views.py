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
    template_name = 'spam/spam.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = 'date_created'
    context_object_name = 'spam'

    def __init__(self):
        self.status = str(Comment.FLAGGED)
        super(SpamList, self).__init__()

    def get_queryset(self):
        self.status = self.request.GET.get('status', u'1')
        query = (
            Q('reports', 'ne', {}) &
            Q('reports', 'ne', None) &
            Q('spam_status', 'eq', int(self.status))
        )
        return Comment.find(query).sort(self.ordering)

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(queryset)
        paginator, page, queryset, is_paginated = self.paginate_queryset(
            queryset, page_size)
        context = {
            'spam': map(serialize_comment, queryset),
            'page': page,
            'status': self.status,
            'page_number': page.number
        }
        return super(SpamList, self).get_context_data(**context)


class SpamDetail(FormView):
    form_class = ConfirmForm
    template_name = 'spam/comment.html'

    def __init__(self):
        self.spam_id = None
        self.page = 1
        self.item = None
        super(SpamDetail, self).__init__()

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            return super(SpamDetail, self).get(request, *args, **kwargs)
        except AttributeError:
            return page_not_found(request)  # TODO: 1.9 update to have exception with node/user 404.html will be added

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        try:
            self.get_context_data(**kwargs)
        except AttributeError:
            return page_not_found(request)  # TODO: 1.9 update to have exception
        return super(SpamDetail, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        self.spam_id = self.kwargs['spam_id']
        self.item = Comment.load(self.spam_id)
        self.page = self.request.GET.get('page', 1)
        kwargs = super(SpamDetail, self).get_context_data(**kwargs)
        kwargs.setdefault('page_number', self.page)
        kwargs.setdefault('comment', serialize_comment(self.item))
        return kwargs

    def form_valid(self, form):
        if int(form.cleaned_data.get('confirm')) == Comment.SPAM:
            self.item.confirm_spam(save=True)
        else:
            self.item.confirm_ham(save=True)
        return super(SpamDetail, self).form_valid(form)

    @property
    def success_url(self):
        return '{}?page={}'.format(
            reverse('spam:detail', kwargs={'spam_id': self.spam_id}),
            self.page
        )


@login_required
def email(request, spam_id):
    context = {
        'comment': serialize_comment(Comment.load(spam_id), full=True),
        'page_number': request.GET.get('page', 1),
    }
    return render(request, 'spam/email.html', context)

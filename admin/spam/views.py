from __future__ import unicode_literals

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponseNotFound
from django.views.generic import FormView, ListView
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.views.defaults import page_not_found

from modularodm import Q
from website.project.model import Comment
from website.settings import SUPPORT_EMAIL

from admin.common_auth.logs import update_admin_log, CONFIRM_HAM, CONFIRM_SPAM
from admin.spam.serializers import serialize_comment
from admin.spam.forms import EmailForm, ConfirmForm


class EmailFormView(FormView):

    form_class = EmailForm
    template_name = "spam/email.html"
    spam_id = None
    page = 1

    def __init__(self):
        self.spam = None
        super(EmailFormView, self).__init__()

    def get(self, request, *args, **kwargs):
        spam_id = kwargs.get('spam_id', None)
        self.spam_id = spam_id
        self.page = request.GET.get('page', 1)
        try:
            self.spam = serialize_comment(Comment.load(spam_id))
        except (AttributeError, TypeError):
            return HttpResponseNotFound(
                '<h1>Spam comment ({}) not found.</h1>'.format(spam_id)
            )
        form = self.get_form()
        context = {
            'comment': self.spam,
            'page_number': request.GET.get('page', 1),
            'form': form
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        spam_id = kwargs.get('spam_id', None)
        self.spam_id = spam_id
        self.page = request.GET.get('page', 1)
        try:
            self.spam = serialize_comment(Comment.load(spam_id))
        except (AttributeError, TypeError):
            return HttpResponseNotFound(
                '<h1>Spam comment ({}) not found.</h1>'.format(spam_id)
            )
        return super(EmailFormView, self).post(request, *args, **kwargs)

    def get_initial(self):
        self.initial = {
            'author': self.spam['author'].fullname,
            'email': [(r, r) for r in self.spam['author'].emails],
            'subject': 'Reports of spam',
            'message': render(
                None,
                'spam/email_template.html',
                {'item': self.spam}
            ).content,
        }
        return super(EmailFormView, self).get_initial()

    def form_valid(self, form):
        send_mail(
            subject=form.cleaned_data.get('subject').strip(),
            message=form.cleaned_data.get('message'),
            from_email=SUPPORT_EMAIL,
            recipient_list=[form.cleaned_data.get('email')]
        )
        return super(EmailFormView, self).form_valid(form)

    @property
    def success_url(self):
        return reverse('spam:detail', kwargs={'spam_id': self.spam_id}) + '?page={}'.format(self.page)


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
            Q('spam_status', 'eq', int(self.request.GET.get('status', '1')))
        )
        return Comment.find(query).sort(self.ordering)

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(queryset)
        paginator, page, queryset, is_paginated = self.paginate_queryset(
            queryset, page_size)
        kwargs.setdefault('spam', map(serialize_comment, queryset))
        kwargs.setdefault('page', page)
        kwargs.setdefault('status', self.request.GET.get('status', '1'))
        kwargs.setdefault('page_number', page.number)
        return super(SpamList, self).get_context_data(**kwargs)


class UserSpamList(SpamList):
    template_name = 'spam/user.html'

    def get_queryset(self):
        query = (
            Q('reports', 'ne', {}) &
            Q('reports', 'ne', None) &
            Q('user', 'eq', self.kwargs.get('user_id', None)) &
            Q('spam_status', 'eq', int(self.request.GET.get('status', '1')))
        )
        return Comment.find(query).sort(self.ordering)

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(queryset)
        paginator, page, queryset, is_paginated = self.paginate_queryset(
            queryset, page_size)
        kwargs.setdefault('spam', map(serialize_comment, queryset))
        kwargs.setdefault('page', page)
        kwargs.setdefault('status', self.request.GET.get('status', '1'))
        kwargs.setdefault('page_number', page.number)
        kwargs.setdefault('user_id', self.kwargs.get('user_id', None))
        return super(UserSpamList, self).get_context_data(**kwargs)


class SpamDetail(FormView):
    form_class = ConfirmForm
    template_name = 'spam/detail.html'

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            return super(SpamDetail, self).get(request, *args, **kwargs)
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    'Spam with id "{}" not found.'.format(
                        kwargs.get('spam_id', 'None'))
                )
            )

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        try:
            return super(SpamDetail, self).post(request, *args, **kwargs)
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    'Spam with id "{}" not found.'.format(
                        kwargs.get('spam_id', 'None'))
                )
            )

    def get_context_data(self, **kwargs):
        item = Comment.load(self.kwargs.get('spam_id'))
        kwargs = super(SpamDetail, self).get_context_data(**kwargs)
        kwargs.setdefault('page_number', self.request.GET.get('page', 1))
        kwargs.setdefault('comment', serialize_comment(item))
        kwargs.setdefault('status', self.request.GET.get('status', u'1'))
        return kwargs

    def form_valid(self, form):
        spam_id = self.kwargs.get('spam_id')
        item = Comment.load(spam_id)
        if int(form.cleaned_data.get('confirm')) == Comment.SPAM:
            item.confirm_spam(save=True)
            log_message = 'Confirmed SPAM: {}'.format(spam_id)
            log_action = CONFIRM_SPAM
        else:
            item.confirm_ham(save=True)
            log_message = 'Confirmed HAM: {}'.format(spam_id)
            log_action = CONFIRM_HAM
        update_admin_log(
            user_id=self.request.user.id,
            object_id=spam_id,
            object_repr='Comment',
            message=log_message,
            action_flag=log_action
        )
        return super(SpamDetail, self).form_valid(form)

    @property
    def success_url(self):
        return '{}?page={}&status={}'.format(
            reverse(
                'spam:detail',
                kwargs={'spam_id': self.kwargs.get('spam_id')}
            ),
            self.request.GET.get('page', 1),
            self.request.GET.get('status', '1')
        )

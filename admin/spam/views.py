from __future__ import unicode_literals

from django.shortcuts import render
from django.core.mail import send_mail
from django.views.generic import FormView, ListView
from django.http import Http404

from modularodm import Q
from website.project.model import Comment
from website.settings import SUPPORT_EMAIL

from admin.base.utils import OSFAdmin
from admin.common_auth.logs import (
    update_admin_log,
    CONFIRM_HAM,
    CONFIRM_SPAM,
    USER_EMAILED,
)
from admin.spam.serializers import serialize_comment
from admin.spam.forms import EmailForm, ConfirmForm
from admin.spam.templatetags.spam_extras import reverse_spam_detail

STATUS = dict(
    UNKNOWN=Comment.UNKNOWN,
    SPAM=Comment.SPAM,
    HAM=Comment.HAM,
    FLAGGED=Comment.FLAGGED,
)


class EmailFormView(OSFAdmin, FormView):
    """ Allow authorized admin user to Email spammers, use judiciously

    Gets user data and supplies email template. Logs mail sent to user.
    """
    form_class = EmailForm
    template_name = 'spam/email.html'

    def get_context_data(self, **kwargs):
        spam_id = self.kwargs.get('spam_id')
        try:
            kwargs.setdefault('comment',
                              serialize_comment(Comment.load(spam_id)))
        except AttributeError:
            raise Http404('Spam with id {} not found.'.format(spam_id))
        kwargs.setdefault('page_number', self.request.GET.get('page', '1'))
        kwargs.setdefault('status', self.request.GET.get('status', '1'))
        return super(EmailFormView, self).get_context_data(**kwargs)

    def get_initial(self):
        spam_id = self.kwargs.get('spam_id')
        try:
            spam = serialize_comment(Comment.load(spam_id))
        except AttributeError:
            raise Http404('Spam with id {} not found.'.format(spam_id))
        self.initial = {
            'author': spam['author'].fullname,
            'email': [(r, r) for r in spam['author'].emails],
            'subject': 'Reports of spam',
            'message': render(
                None,
                'spam/email_template.html',
                {'item': spam}
            ).content,
        }
        return super(EmailFormView, self).get_initial()

    def form_valid(self, form):
        message = form.cleaned_data.get('message')
        email = form.cleaned_data.get('email')
        send_mail(
            subject=form.cleaned_data.get('subject').strip(),
            message=message,
            from_email=SUPPORT_EMAIL,
            recipient_list=[email]
        )
        update_admin_log(
            user_id=self.request.user.id,
            object_id=self.kwargs.get('spam_id'),
            object_repr='Comment',
            message='User with email {} sent this message: {}'.format(
                email, message
            ),
            action_flag=USER_EMAILED
        )
        return super(EmailFormView, self).form_valid(form)

    @property
    def success_url(self):
        return reverse_spam_detail(
            self.kwargs.get('spam_id'),
            page=self.request.GET.get('page', '1'),
            status=self.request.GET.get('status', '1')
        )


class SpamList(OSFAdmin, ListView):
    """ Allow authorized admin user to see the things people have marked as spam

    Interface with OSF database. No admin models.
    """
    template_name = 'spam/spam_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = '-date_last_reported'
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
    """ Allow authorized admin user to see the comments a user has had
     marked spam

    Interface with OSF database. No admin models.
    """
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
        kwargs.setdefault('user_id', self.kwargs.get('user_id', None))
        return super(UserSpamList, self).get_context_data(**kwargs)


class SpamDetail(OSFAdmin, FormView):
    """ Allow authorized admin user to see details of reported spam.

    Interface with OSF database. Logs action (confirming spam) on admin db.
    """
    form_class = ConfirmForm
    template_name = 'spam/detail.html'

    def get_context_data(self, **kwargs):
        spam_id = self.kwargs.get('spam_id')
        kwargs = super(SpamDetail, self).get_context_data(**kwargs)
        try:
            kwargs.setdefault('comment',
                              serialize_comment(Comment.load(spam_id)))
        except AttributeError:
            raise Http404('Spam with id "{}" not found.'.format(spam_id))
        kwargs.setdefault('page_number', self.request.GET.get('page', '1'))
        kwargs.setdefault('status', self.request.GET.get('status', '1'))
        kwargs.update(STATUS)  # Pass status in to check against
        return kwargs

    def form_valid(self, form):
        spam_id = self.kwargs.get('spam_id')
        item = Comment.load(spam_id)
        try:
            if int(form.cleaned_data.get('confirm')) == Comment.SPAM:
                item.confirm_spam()
                item.is_deleted = True
                log_message = 'Confirmed SPAM: {}'.format(spam_id)
                log_action = CONFIRM_SPAM
            else:
                item.confirm_ham()
                item.is_deleted = False
                log_message = 'Confirmed HAM: {}'.format(spam_id)
                log_action = CONFIRM_HAM
            item.save()
        except AttributeError:
            raise Http404('Spam with id "{}" not found.'.format(spam_id))
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
        return reverse_spam_detail(
            self.kwargs.get('spam_id'),
            page=self.request.GET.get('page', '1'),
            status=self.request.GET.get('status', '1')
        )

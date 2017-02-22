from __future__ import unicode_literals

from django.views.generic import FormView, ListView, DetailView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import Http404

from osf.models.comment import Comment
from osf.models.user import OSFUser
from website.project.spam.model import SpamStatus

from osf.models.admin_log_entry import (
    update_admin_log,
    CONFIRM_HAM,
    CONFIRM_SPAM,
)
from admin.spam.serializers import serialize_comment
from admin.spam.forms import ConfirmForm
from admin.spam.templatetags.spam_extras import reverse_spam_detail


class EmailView(PermissionRequiredMixin, DetailView):
    template_name = 'spam/email.html'
    context_object_name = 'spam'
    permission_required = 'common_auth.view_spam'

    def get_object(self, queryset=None):
        spam_id = self.kwargs.get('spam_id')
        try:
            return serialize_comment(Comment.load(spam_id))
        except AttributeError:
            raise Http404('Spam with id {} not found.'.format(spam_id))


class SpamList(PermissionRequiredMixin, ListView):
    """ Allow authorized admin user to see the things people have marked as spam

    Interface with OSF database. No admin models.
    """
    template_name = 'spam/spam_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = '-date_last_reported'
    context_object_name = 'spam'
    permission_required = 'common_auth.view_spam'
    raise_exception = True

    def get_queryset(self):
        return Comment.objects.filter(
            spam_status=int(self.request.GET.get('status', '1'))
        ).exclude(reports={}).exclude(reports=None)

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
        user = OSFUser.load(self.kwargs.get('user_id', None))

        return Comment.objects.filter(
            spam_status=int(self.request.GET.get('status', '1')),
            user=user
        ).exclude(reports={}).exclude(reports=None).order_by(self.ordering)

    def get_context_data(self, **kwargs):
        kwargs.setdefault('user_id', self.kwargs.get('user_id', None))
        return super(UserSpamList, self).get_context_data(**kwargs)


class SpamDetail(PermissionRequiredMixin, FormView):
    """ Allow authorized admin user to see details of reported spam.

    Interface with OSF database. Logs action (confirming spam) on admin db.
    """
    form_class = ConfirmForm
    template_name = 'spam/detail.html'
    permission_required = 'common_auth.view_spam'
    raise_exception = True

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
        kwargs.update({'SPAM_STATUS': SpamStatus})  # Pass status in to check against
        return kwargs

    def form_valid(self, form):
        spam_id = self.kwargs.get('spam_id')
        item = Comment.load(spam_id)
        try:
            if int(form.cleaned_data.get('confirm')) == SpamStatus.SPAM:
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

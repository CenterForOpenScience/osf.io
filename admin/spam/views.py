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

from .serializers import serialize_comment
from .forms import EmailForm, ConfirmForm


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

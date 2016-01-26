from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.views.generic import FormView
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotFound

from modularodm import Q
from website.project.model import Comment
from website.settings import SUPPORT_EMAIL

from .serializers import serialize_comment
from .forms import EmailForm


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


def get_spam_list():
    query = (
        Q('reports', 'ne', {}) &
        Q('reports', 'ne', None)
    )
    return Comment.find(query).sort('date_created')


@login_required
def spam_list(request):
    paginator = Paginator(get_spam_list(), 10)

    page_number = request.GET.get('page', 1)
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    context = {
        'spam': map(serialize_comment, page),
        'page': page,
        'page_number': page_number,
    }
    return render(request, 'spam/spam.html', context)


@login_required
def spam_detail(request, spam_id):
    context = {
        'comment': serialize_comment(Comment.load(spam_id)),
        'page_number': request.GET.get('page', 1),
    }
    return render(request, 'spam/comment.html', context)

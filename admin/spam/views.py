from django.shortcuts import render, render_to_response
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from django.views.generic import FormView

from .serializers import serialize_comments, retrieve_comment
from .forms import EmailForm


class EmailFormView(FormView):

    form_class = EmailForm
    template_name = ""  # TODO: <-
    success_url = ''  # TODO <-


@login_required
def spam_list(request):
    comment_list = serialize_comments()
    paginator = Paginator(comment_list, 10)

    page = request.GET.get('page', 1)
    try:
        comments = paginator.page(page)
    except PageNotAnInteger:
        comments = paginator.page(1)
    except EmptyPage:
        comments = paginator.page(paginator.num_pages)
    return render_to_response('spam/spam.html', {'comments': comments})


@login_required
def spam_detail(request, spam_id):
    comment = retrieve_comment(spam_id)
    context = {'comment': comment}
    return render(request, 'spam/comment.html', context)


@login_required
def spam_sub_list(request, spam_ids):
    comments = None
    context = {'comments': comments}
    # should test for impossibilities such as many users. Return error page.
    return render(request, 'spam/sub_list.html', context)


@login_required
def email(request, spam_id):
    comment = retrieve_comment(spam_id, full_user=True)
    context = {'comment': comment}
    return render(request, 'spam/email.html', context)

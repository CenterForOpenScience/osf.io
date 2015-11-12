from django.http import HttpResponse
from django.shortcuts import render

from .serializers import serialize_comments, retrieve_comment


def spam_list(request):
    comments = serialize_comments()
    context = {'comments': comments}
    return render(request, 'spam/spam.html', context)


def spam_detail(request, spam_id):
    comment = retrieve_comment(spam_id)
    context = {'comment': comment}
    return render(request, 'spam/comment.html', context)


def spam_sub_list(request, spam_ids):
    comments = None
    context = {'comments': comments}
    # should test for impossibilities such as many users. Return error page.
    return render(request, 'spam/sub_list.html', context)


def email(request, spam_id):
    comment = retrieve_comment(spam_id, full_user=True)
    context = {'comment': comment}
    return render(request, 'spam/email.html', context)

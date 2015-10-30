from django.http import HttpResponse
from django.shortcuts import render

from .serializers import serialize_comments, retrieve_comment


def spam_list(request):
    comments = serialize_comments()
    context = {'comments': comments}
    return render(request, 'spam/spam.html', context)
    # return HttpResponse('This is a list of spam:{}'.format(' *** '.join(serialize_comments())))


def spam_detail(request, spam_id):
    comment = retrieve_comment(spam_id)
    context = {'comment': comment}
    return render(request, 'spam/comment.html', context)


def email(request, spam_id):
    comment = retrieve_comment(spam_id)
    context = {'comment': comment}
    return render(request, 'spam/email.html', context)

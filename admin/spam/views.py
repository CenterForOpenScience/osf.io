from django.http import HttpResponse
from django.shortcuts import render

from .serializers import serialize_comments


def spam_list(request):
    comments = serialize_comments()
    context = {'comments': comments}
    return render(request, 'spam/spam.html', context)
    # return HttpResponse('This is a list of spam:{}'.format(' *** '.join(serialize_comments())))


def spam_detail(request, spam_id):
    return HttpResponse('Looking at spam {}'.format(spam_id))

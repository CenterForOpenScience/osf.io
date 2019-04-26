from django.http import HttpResponse


def all_users(request, **kwargs):
    return HttpResponse('Hello world!')

def user(request, **kwargs):
    return HttpResponse('Hello world!' + ' from user_id:' + kwargs['guid'])

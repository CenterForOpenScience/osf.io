from django.http import HttpResponse


def root(request):
    return HttpResponse("Will probably need to put some front end Auth on this.")

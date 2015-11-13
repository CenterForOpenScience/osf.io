from django.contrib.auth.decorators import login_required
from django.shortcuts import render

#def root(request):
#   return HttpResponse("Will probably need to put some front end Auth on this.")

@login_required
def home(request):
    return render(request, 'home.html', {'user': request.user})

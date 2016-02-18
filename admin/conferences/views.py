from django.shortcuts import render, redirect
from django.contrib import messages
from forms import ConferenceForm
from .models import Conference

# Create your views here.
def create_conference(request):
    if request.user.is_staff:
        form = ConferenceForm(request.POST)
        if request.method == 'POST':
            if form.is_valid():
                new_conference = form.save()
                # Save with commit=False to do stuff here if need be

                # new_conference.save()
                return redirect('conferences:create_conference')
            else:
                print(form.errors)
                messages.error(request, 'Test..')

                return redirect('conferences:create_conference')
        else:
            context = {'form': form}
            return render(request, 'conferences/create_conference.html', context)
    else:
        messages.error(request, 'You do not have permission to access that page.')
        return redirect('auth:login')


def populate_conferences():
    # objects = Conference.objects.all()
    # for obj in objects:
    for meeting, attrs in MEETING_DATA.iteritems():
        meeting = meeting.strip() #obj.endpoint.strip()
        admin_emails = attrs.pop('admins', []) # obj.admins
        admin_objs = []
        for email in admin_emails:
            try:
                user = User.find_one(Q('username', 'iexact', email))
                admin_objs.append(user)
            except ModularOdmException:
                raise RuntimeError('Username {0!r} is not registered.'.format(email))

        custom_fields = attrs.pop('field_names', {}) # obj.field_names

        conf = Conference(
            endpoint=meeting, admins=admin_objs, **attrs # =
        ) #
        conf.field_names.update(custom_fields)
        try:
            conf.save()
        except ModularOdmException:
            conf = Conference.find_one(Q('endpoint', 'eq', meeting))
            for key, value in attrs.items():
                if isinstance(value, dict):
                    current = getattr(conf, key)
                    current.update(value)
                    setattr(conf, key, current)
                else:
                    setattr(conf, key, value)
            conf.admins = admin_objs
            changed_fields = conf.save()
            if changed_fields:
                print('Updated {}: {}'.format(meeting, changed_fields))
        else:
            print('Added new Conference: {}'.format(meeting))

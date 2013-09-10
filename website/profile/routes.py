from framework import (
    abort,
    get,
    get_current_user,
    get_user,
    jsonify,
    must_be_logged_in,
    post,
    render,
    request,
)
from framework.forms.utils import sanitize


@get('/profile')
@must_be_logged_in
def profile_view(*args, **kwargs):
    user = kwargs['user']
    return render(filename="profile.mako", profile=user, user=user)


@get('/profile/<user_id>')
def profile_view_id(user_id):
    profile = get_user(id=user_id)
    user = get_current_user()
    if profile:
        return render(filename="profile.mako", profile=profile, user=user)
    return abort(404)


@post('/profile/<user_id>/edit')
@must_be_logged_in
def edit_profile(*args, **kwargs):
    user = kwargs['user']
    
    form = request.form

    if form.get('name') == 'fullname' and form.get('value', '').strip():
        user.fullname = sanitize(form['value'])
        user.save()

    return jsonify({'response': 'success'})


@get('/settings')
@must_be_logged_in
def settings(*args, **kwargs):
    user = kwargs['user']
    return render(filename="settings.mako",user=user,prettify=True)
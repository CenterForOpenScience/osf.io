from framework import (
    abort,
    get,
    get_current_user,
    get_user,
    jsonify,
    must_be_logged_in,
    post,
    redirect,
    render,
    request,
)
from framework.forms.utils import sanitize

from website.models import ApiKey

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

@post('/settings/create_key/')
@must_be_logged_in
def create_user_key(*args, **kwargs):

    # Generate key
    api_key = ApiKey(label=request.form['label'])
    api_key.save()

    # Append to user
    user = get_current_user()
    user.api_keys.append(api_key)
    user.save()

    # Return response
    return jsonify({'response': 'success'})

@post('/settings/remove_key/')
@must_be_logged_in
def revoke_user_key(*args, **kwargs):

    # Load key
    api_key = ApiKey.load(request.form['key'])

    # Remove from user
    user = get_current_user()
    user.api_keys.remove(api_key)
    user.save()

    # Return response
    return jsonify({'response': 'success'})

@get('/settings/key_history/<kid>')
@must_be_logged_in
def user_key_history(*args, **kwargs):

    api_key = ApiKey.load(kwargs['kid'])
    return render(
        filename='keyhistory.mako',
        api_key=api_key,
        user=kwargs['user'],
        route='/settings',
    )
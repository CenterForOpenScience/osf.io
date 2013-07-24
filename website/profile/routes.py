from framework import *

@get('/profile')
@must_be_logged_in
def profile_view(*args, **kwargs):
    user = kwargs['user']
    return render(filename="profile.mako", profile=user, user=user)

@get('/profile/<id>')
def profile_view_id(id):
    profile = get_user(id=id)
    user = get_current_user()
    return render(filename="profile.mako", profile=profile, user=user)

@post('/profile/<id>/edit')
@must_be_logged_in
def edit_profile(*args, **kwargs):
    user = kwargs['user']
    
    form = request.form
    original_fullname = user.fullname

    if form['name'] == 'fullname' and not form['value'].strip() == '':
        user.fullname = form['value']
        user.save()

    return jsonify({'response': 'success'})

@get('/settings')
@must_be_logged_in
def settings(*args, **kwargs):
	user = kwargs['user']
	return render(filename="settings.mako",user=user,prettify=True)
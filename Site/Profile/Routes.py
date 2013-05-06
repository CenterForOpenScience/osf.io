from Framework import *

@get('/profile')
@mustBeLoggedIn
def profile_view(*args, **kwargs):
    user = kwargs['user']
    return render(filename="profile.mako", profile=user, user=user)

@get('/profile/<id>')
def profile_view_id(id):
    profile = getUser(id=id)
    user = getCurrentUser()
    return render(filename="profile.mako", profile=profile, user=user)

@post('/profile/<id>/edit')
@mustBeLoggedIn
def edit_profile(*args, **kwargs):
    user = kwargs['user']
    
    form = request.form
    original_fullname = user.fullname

    if form['name'] == 'fullname' and not form['value'].strip() == '':
        user.fullname = form['value']
        user.save()

    return jsonify({'response': 'success'})

@get('/settings')
@mustBeLoggedIn
def settings(*args, **kwargs):
	user = kwargs['user']
	return render(filename="settings.mako",user=user,prettify=True)
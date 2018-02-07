## How to run the admin interface

1. Set up your environment
**note** -- these steps are also covered in the Application Runtime and Quickstart sections of the OSF's docker-compose README,
so you might not need to repeat them if you already have the base OSF docker containers running.
- Make sure the requirements are up to date with `docker-compose up requirements`
- Run the admin assets docker container with `docker-compose up -d admin_assets`
- Run the admin container with `docker-compose up -d admin`

2. Set up a superuser
**note** - your superuser will have all permissions, and will be able to access the admin's admin interface.
If you are manually testing functionality for permissions views, do not log in to the admin as your superuser, as you will always have all permissions.
- Open up the OSF shell with `docker-compose run --rm web invoke shell`
- Select the already existing OSF User you'd like to make an admin superuser with `user = OSFUser.objects.get(username=<your_user@cos.io>)`
- Set that user to be a superuser and staff with `user.is_superuser = True` and `user.is_staff = True`
- Save your user with `user.save()`
- Commit the changes with `commit()`

3. Update your ALLOWED_HOSTS
- If you haven't already, create an admin local.py by copying `admin/base/settings/defaults.py` into `admin/base/settings/local.py`
- Add 'localhost' to `ALLOWED_HOSTS` in your `admin/base/settings/local.py`

4. Log in to the admin
- Visit the admin at `http://localhost:8001/`
- Log in with your OSF User's username and password

5. Add other admin users
- Visit the admin user form at the top right under your username
- Add users by their OSF guid
- Select the permissions you'd like your user to have using the checkboxes, and click submit
- To update an existing user, enter their OSF guid and re-check the boxes for the new permissions you'd like them to have.

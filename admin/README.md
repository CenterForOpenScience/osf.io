## How to run the admin interface

- Start in the top osf directory
- Run `invoke requirements`
- Run `invoke admin.assets -d` optional `-dw` to catch updates if you are working on JS.
- Run `invoke admin.manage migrate`
- Run `invoke admin.manage createsuperuser` and follow directions
    - If any of these invoke scripts require input but `invoke` isn't allowing it use:
        - `setenv DJANGO_SETTINGS_MODULE "admin.base.settings"`
        - **or**
        - `export DJANGO_SETTINGS_MODULE="admin.base.settings"`
        - `cd admin`
        - `python ../manage.py <action>`
- Run `invoke adminserver` This will run it on default port 8001
- In your browser navigate to `localhost:8001/admin`
- Log in with your superuser

### Prereg

If you need to do local prereg work then you should really just add a user with the correct permissions.

- Logged in as your superuser, click on your email in the top right corner.
- Click on the `Admin-User Registration`
- Fill out the form and submit. Take care of form errors.
- Log out
- Find the email in the console or email server and copy/follow the link.
- Set a new password
- Log in as the new user.
- This user now has access to local prereg registrations.


### Set Up Users via the shell

Your Admin users will need to be added to different Groups before they can do anything.
If you'd like to manually set up a user to be a part of different groups using the shell, follow these steps:

- Open the admin's shell with `invoke admin.manage shell`
- Import the `MyUser` model with `from admin.common_auth.models import MyUser`
- Import the `Group` model with `from django.contrib.auth.models import Group`
- Filter for the user you'd like to use by email (or other field) with `MyUser.objects.filter(email='your@email.com')`
- Set your user's group relationship by filtering for the appropriate group by name and adding it to your user's group.
    - Choices for name are `prereg_group`, `osf_admin`, and `osf_group`
    - To make your user a part of the `osf_admin` group:
        user = MyUser.objects.filter(email='your@email.com')
        user.groups.add(Groups.objects.filter(name='osf_admin'))
        user.save()

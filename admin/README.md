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

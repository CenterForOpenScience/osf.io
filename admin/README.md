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

If you need to do prereg work then you need to add a group and add an OSF id to your admin user's profile.

- Navigate to `localhost:8001/admin/django_admin/`
- Go to groups and add `prereg_group` without any other permissions
- save
- Go to **My users** and go into the user that needs to be a prereg admin
- Add an existing user id to **Osf id**
- Select **prereg_group** from the groups list and add it to **Chosen groups**
- save

You should now be able to see the **OSF Prereg** link on the left when you navigate back to `localhost:8001/admin`


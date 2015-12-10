from datetime import datetime
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models

from website.models import User as OsfUserModel


class MyUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        user = self.create_user(email,
            password=password, )
        user.is_superuser = True
        user.is_admin = True
        user.is_staff = True
        user.is_active = True
        user.save(using=self._db)
        return user

    def prereg_users(self):
        return self.filter(groups__name='prereg_group')


class MyUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )

    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=datetime.now)
    confirmed = models.BooleanField(default=False)
    osf_id = models.CharField(default=False, max_length=10, blank=True)

    objects = MyUserManager()

    USERNAME_FIELD = 'email'

    def get_full_name(self):
        # The user is identified by their email address
        return self.email

    def get_short_name(self):
        # The user is identified by their email address
        return self.email

    def __unicode__(self):
        return self.email

    class Meta:
        ordering = ['email']

    # Todo: implement this if needed
    # @property
    # def is_staff(self):
    #     "Is the user a member of staff?"
    #     return self.is_admin

    @property
    def osf_user(self):
        if not self.osf_id:
            raise RuntimeError('This user does not have an associated Osf User')
        return OsfUserModel.load(self.osf_id)

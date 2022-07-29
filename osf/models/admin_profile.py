from django.db import models


class AdminProfile(models.Model):
    primary_identifier_name = 'id'

    user = models.OneToOneField('osf.OSFUser', related_name='admin_profile',
                                on_delete=models.CASCADE)

    desk_token = models.CharField(max_length=45, blank=True)
    desk_token_secret = models.CharField(max_length=45, blank=True)

    def __unicode__(self):
        return self.user.username

    class Meta:
        # custom permissions for use in the OSF Admin App
        permissions = (
            ('mark_spam', 'Can mark comments, projects and registrations as spam'),
            ('view_spam', 'Can view nodes, comments, and projects marked as spam'),
            ('view_metrics', 'Can view metrics on the OSF Admin app'),
            ('view_desk', 'Can view details about Desk users'),
            ('delete_preprintrequest', 'Can delete preprints withdrawal requests'),
            ('change_preprintrequest', 'Can update preprints withdrawal requests'),
        )

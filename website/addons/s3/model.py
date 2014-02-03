'''
Created on Jan 7, 2014

@author: seto
'''
"""

"""

from framework import fields

from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase

from utils import get_bucket_drop_down, serialize_bucket

from api import S3Wrapper


class AddonS3UserSettings(AddonUserSettingsBase):

    access_key = fields.StringField()
    secret_key = fields.StringField()

    def to_json(self, user):
        rv = super(AddonS3UserSettings, self).to_json(user)
        rv.update({
            'access_key': self.access_key or '',
            'secret_key': self.secret_key or '',
            'has_auth': True if self.access_key and self.secret_key else False,
        })
        return rv

    @property
    def has_auth(self):
        return True if self.access_key and self.secret_key else False


class AddonS3NodeSettings(AddonNodeSettingsBase):

    bucket = fields.StringField()
    node_access_key = fields.StringField()
    node_secret_key = fields.StringField()

    #'Special fields'
    registration_data = fields.DictionaryField()

    # TODO Considering removing node_ in naming
    def to_json(self, user):

        rv = super(AddonS3NodeSettings, self).to_json(user)
        s3_user_settings = user.get_addon('s3')

        rv.update({
            'bucket': self.bucket or '',
            'has_bucket': self.bucket is not None,
            'access_key': self.node_access_key or '',
            'secret_key': self.node_secret_key or '',
            'user_has_auth': False,
            'node_auth': self.node_auth,
        })
        if s3_user_settings:
            rv['user_has_auth'] = True if s3_user_settings.has_auth else False
            rv['bucket_list'] = get_bucket_drop_down(
                s3_user_settings, self.node_auth)

        return rv

    @property
    def node_auth(self):
        return True if self.node_access_key and self.node_secret_key else False

    @property
    def is_registration(self):
        return True if self.registration_data else False

    def after_register(self, node, registration, user, save=True):
        """

        :param Node node: Original node
        :param Node registration: Registered node
        :param User user: User creating registration
        :param bool save: Save settings after callback
        :return tuple: Tuple of cloned settings and alert message

        """

        clone, message = super(AddonS3NodeSettings, self).after_register(
            node, registration, user, save=False
        )

        if self.bucket and self.node_auth:
            clone.registration_data['bucket'] = self.bucket
            clone.registration_data['keys'] = serialize_bucket(S3Wrapper.from_addon(self))

        if save:
            clone.save()

        return clone, message

    def before_register(self, node, user):
        """

        :param Node node:
        :param User user:
        :return str: Alert message

        """
        if user.get_addon('s3').has_auth:
            return (
                'Registering {cat} "{title}" will copy the authentication for its '
                'Amazon Simple Storage add-on to the registered {cat}. '
                'As well as turning versioning on in your bucket,'
                'which may result in larger charges from Amazon'
            ).format(
                cat=node.project_or_component,
                title=node.title,
                bucket_name=self.bucket,
            )

    def after_fork(self, node, fork, user, save=True):
        """

        :param Node node: Original node
        :param Node fork: Forked node
        :param User user: User creating fork
        :param bool save: Save settings after callback
        :return tuple: Tuple of cloned settings and alert message

        """
        clone, _ = super(AddonS3NodeSettings, self).after_fork(
            node, fork, user, save=False
        )

        # Copy authentication if authenticated by forking user
        if user.get_addon('s3') and node.get_addon('s3').owner == user:
            clone.node_access_key = self.node_access_key
            clone.node_secret_key = self.node_secret_key
            clone.bucket = self.bucket
            message = (
                'Amazon Simple Storage authorization copied to forked {cat}.'
            ).format(
                cat=fork.project_or_component,
            )
        else:
            clone.node_access_key = None
            clone.node_secret_key = None
            clone.bucket = None
            message = (
                'Amazon Simple Storage authorization not copied to forked {cat}. You may '
                'authorize this fork on the <a href={url}>Settings</a> '
                'page.'
            ).format(
                cat=fork.project_or_component,
                url=fork.url + 'settings/'
            )

        if save:
            clone.save()

        return clone, message

    def before_fork(self, node, user):
        """

        :param Node node:
        :param User user:
        :return str: Alert message

        """

        if user.get_addon('s3') and node.get_addon('s3').owner == user:
            return (
                'Because you have authenticated the S3 add-on for this '
                '{cat}, forking it will also transfer your authorization to '
                'the forked {cat}.'
            ).format(
                cat=node.project_or_component,
            )
        return (
            'Because this S3 add-on has been authenticated by a different '
            'user, forking it will not transfer authentication to the forked '
            '{cat}.'
        ).format(
            cat=node.project_or_component,
        )


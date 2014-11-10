'''
Created on Jan 7, 2014

@author: seto
'''
"""

"""

import os

from boto.exception import BotoServerError
from modularodm import fields

from framework.auth.core import Auth

from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase, GuidFile
from website.addons.s3.api import S3Wrapper
from website.addons.s3.utils import get_bucket_drop_down, serialize_bucket, remove_osf_user


class S3GuidFile(GuidFile):

    path = fields.StringField(index=True)

    @property
    def file_url(self):
        if self.path is None:
            raise ValueError('Path field must be defined.')
        return os.path.join('s3', self.path)


class AddonS3UserSettings(AddonUserSettingsBase):

    s3_osf_user = fields.StringField()
    access_key = fields.StringField()
    secret_key = fields.StringField()

    def to_json(self, user):
        rv = super(AddonS3UserSettings, self).to_json(user)
        rv['has_auth'] = self.has_auth
        return rv

    @property
    def has_auth(self):
        return bool(self.access_key and self.secret_key)

    def remove_iam_user(self):
        """Remove IAM user from Amazon.

        :return: True if successful, False if failed with expected error;
            else uncaught exception is raised

        """
        try:
            remove_osf_user(self)
            return True
        except BotoServerError as error:
            if error.code in ['InvalidClientTokenId', 'ValidationError', 'AccessDenied']:
                return False
            raise

    def revoke_auth(self, save=False):
        for node_settings in self.addons3nodesettings__authorized:
            node_settings.deauthorize(save=True)
        rv = self.remove_iam_user() if self.has_auth else True
        self.s3_osf_user, self.access_key, self.secret_key = None, None, None

        if save:
            self.save()
        return rv

    def delete(self, save=True):
        self.revoke_auth(save=False)
        super(AddonS3UserSettings, self).delete(save=save)


class AddonS3NodeSettings(AddonNodeSettingsBase):

    registration_data = fields.DictionaryField()
    bucket = fields.StringField()
    user_settings = fields.ForeignField(
        'addons3usersettings', backref='authorized'
    )

    def authorize(self, user_settings, save=False):
        self.user_settings = user_settings
        self.owner.add_log(
            action='s3_node_authorized',
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
            },
            auth=Auth(user_settings.owner),
        )
        if save:
            self.save()

    def deauthorize(self, auth=None, log=True, save=False):
        self.registration_data = None
        self.bucket = None
        self.user_settings = None

        if log:
            self.owner.add_log(
                action='s3_node_deauthorized',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                },
                auth=auth,
            )
        if save:
            self.save()

    def delete(self, save=True):
        self.deauthorize(log=False, save=False)
        super(AddonS3NodeSettings, self).delete(save=save)

    def to_json(self, user):
        rv = super(AddonS3NodeSettings, self).to_json(user)

        user_settings = user.get_addon('s3')

        rv.update({
            'bucket': self.bucket or '',
            'has_bucket': self.bucket is not None,
            'user_is_owner': (
                self.user_settings and self.user_settings.owner == user
            ),
            'user_has_auth': bool(user_settings) and user_settings.has_auth,
            'node_has_auth': self.has_auth,
            'owner': None,
            'bucket_list': None,
            'is_registration': self.owner.is_registration,
        })

        if self.has_auth:
            rv['owner'] = self.user_settings.owner.fullname
            rv['owner_url'] = self.user_settings.owner.url
            rv['bucket_list'] = get_bucket_drop_down(self.user_settings)
            rv['node_has_auth'] = True

        return rv

    @property
    def is_registration(self):
        return True if self.registration_data else False

    @property
    def has_auth(self):
        return self.user_settings and self.user_settings.has_auth
        #TODO Update callbacks

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

        #enable_versioning(self)

        if self.bucket and self.has_auth:
            clone.user_settings = self.user_settings
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
        if self.user_settings and self.user_settings.has_auth:
            return (
                'Registering {cat} "{title}" will copy the authentication for its '
                'Amazon Simple Storage add-on to the registered {cat}. '
                # 'As well as turning versioning on in your bucket,'
                # 'which may result in larger charges from Amazon'
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
        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            clone.bucket = self.bucket
            message = (
                'Amazon Simple Storage authorization copied to forked {cat}.'
            ).format(
                cat=fork.project_or_component,
            )
        else:
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

        if self.user_settings and self.user_settings.owner == user:
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

    def before_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:
        :return str: Alert message

        """
        if self.user_settings and self.user_settings.owner == removed:
            return (
                'The Amazon Simple Storage add-on for this {category} is authenticated '
                'by {user}. Removing this user will also remove access '
                'to {bucket} unless another contributor re-authenticates.'
            ).format(
                category=node.project_or_component,
                user=removed.fullname,
                bucket=self.bucket
            )

    def after_remove_contributor(self, node, removed):
        """

        :param Node node:
        :param User removed:
        :return str: Alert message

        """
        if self.user_settings and self.user_settings.owner == removed:
            self.user_settings = None
            self.bucket = None
            self.save()

            return (
                'Because the Amazon Simple Storage add-on for this project was authenticated '
                'by {user}, authentication information has been deleted. You '
                'can re-authenticate on the <a href="{url}settings/">'
                'Settings</a> page.'.format(
                    user=removed.fullname,
                    url=node.url,
                )
            )

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), log=True, save=True)

import os

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from framework import fields
from framework.auth.decorators import Auth
from website.addons.base import AddonNodeSettingsBase, AddonUserSettingsBase
from website.addons.base import GuidFile
from website.addons.dataverse.client import connect, get_studies, get_study, \
    get_dataverses, get_dataverse
from website.addons.dataverse.settings import HOST


class DataverseFile(GuidFile):

    file_id = fields.StringField(required=True, index=True)

    @property
    def file_url(self):
        return os.path.join('dataverse', 'file', self.file_id)

    @classmethod
    def get_or_create(cls, node, path):
        """Get or create a new file record. Return a tuple of the form (obj, created)
        """
        try:
            new = cls.find_one(
                Q('node', 'eq', node) &
                Q('file_id', 'eq', path)
            )
            created = False
        except ModularOdmException:
            # Create new
            new = cls(node=node, file_id=path)
            new.save()
            created = True
        return new, created


class AddonDataverseUserSettings(AddonUserSettingsBase):

    dataverse_username = fields.StringField()
    dataverse_password = fields.StringField()

    @property
    def has_auth(self):
        return bool(self.dataverse_username and self.dataverse_password)

    def delete(self):
        self.clear()
        super(AddonDataverseUserSettings, self).delete()

    def clear(self):
        """Clear settings and deauthorize any associated nodes.

        :param bool delete: Indicates if the settings should be deleted.
        """
        self.dataverse_username = None
        self.dataverse_password = None
        for node_settings in self.addondataversenodesettings__authorized:
            node_settings.deauthorize(Auth(self.owner))
            node_settings.save()
        return self

class AddonDataverseNodeSettings(AddonNodeSettingsBase):

    dataverse_alias = fields.StringField()
    dataverse = fields.StringField()
    study_hdl = fields.StringField()
    study = fields.StringField()

    user_settings = fields.ForeignField(
        'addondataverseusersettings', backref='authorized'
    )

    @property
    def has_auth(self):
        """Whether a dataverse account is associated with this node."""
        return bool(self.user_settings and self.user_settings.has_auth)

    def delete(self):
        self.deauthorize(Auth(self.user_settings.owner), add_log=False)
        super(AddonDataverseNodeSettings, self).delete()

    def deauthorize(self, auth, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.dataverse_alias = None
        self.dataverse = None
        self.study_hdl = None
        self.study = None
        self.user_settings = None

        if add_log:
            node = self.owner
            self.owner.add_log(
                action='dataverse_node_deauthorized',
                params={
                    'project': node.parent_id,
                    'node': node._id,
                },
                auth=auth,
            )

    def to_json(self, user):

        user_settings = user.get_addon('dataverse')

        # Check authorization
        authorized = self.has_auth and user_settings == self.user_settings

        # Check user's connection
        user_connection = connect(
            user_settings.dataverse_username,
            user_settings.dataverse_password,
        ) if user_settings else None

        rv = super(AddonDataverseNodeSettings, self).to_json(user)
        rv.update({
            'connected': False,
            'authorized': authorized,
            'show_submit': False,
            'user_dataverse_connected': user_connection,
            'set_dataverse_url': self.owner.api_url_for('set_dataverse'),
            'set_study_url': self.owner.api_url_for('set_study'),
        })

        if self.user_settings is None:
            return rv

        rv.update({
            'authorized_dataverse_user': self.user_settings.dataverse_username,
            'authorized_user_name': self.user_settings.owner.fullname,
            'authorized_user_url': self.user_settings.owner.absolute_url,
        })

        connection = connect(
            self.user_settings.dataverse_username,
            self.user_settings.dataverse_password,
        )

        if connection is not None:

            # Get list of dataverses and studies
            dataverses = get_dataverses(connection)
            dataverse = get_dataverse(connection, self.dataverse_alias)
            studies = get_studies(dataverse) if dataverse else []
            study = get_study(dataverse, self.study_hdl) \
                if self.study_hdl is not None else None

            rv.update({
                'connected': True,
                'dataverses': [d.title for d in dataverses],
                # TODO: Implement dataverse releasing (after Dataverse 4.0)
                'dv_status': [d.is_released for d in dataverses],
                'dataverse': dataverse.title if dataverse else None,
                'dataverse_alias': dataverse.alias if dataverse else None,
                'dataverse_aliases': [d.alias for d in dataverses],
                'studies': [s.get_id() for s in studies],
                'study_names': [s.title for s in studies],
                'study': self.study,
                'study_hdl': self.study_hdl if study is not None else None,
            })

            if study is not None:
                rv.update({
                    'dataverse_url': os.path.join(
                        'http://', HOST, 'dvn', 'dv', dataverse.alias
                    ),
                    'study_url': os.path.join(
                        'http://', HOST, 'dvn', 'dv', dataverse.alias,
                        'faces', 'study', 'StudyPage.xhtml?globalId=' +
                        study.doi
                    ),
                })

        return rv

    ##### Callback overrides #####

    # Note: Registering Dataverse content is disabled for now
    # def before_register_message(self, node, user):
    #     """Return warning text to display if user auth will be copied to a
    #     registration.
    #     """
    #     category, title = node.project_or_component, node.title
    #     if self.user_settings and self.user_settings.has_auth:
    #         return ('Registering {category} "{title}" will copy Dataverse '
    #                 'add-on authentication to the registered {category}.'
    #                 .format(**locals()))
    #
    # # backwards compatibility
    # before_register = before_register_message

    def before_fork_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        fork.
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.owner == user:
            return ('Because you have authorized the Dataverse add-on for this '
                '{category}, forking it will also transfer your authentication '
                'to the forked {category}.').format(category=category)

        else:
            return ('Because the Dataverse add-on has been authorized by a different '
                    'user, forking it will not transfer authentication to the forked '
                    '{category}.').format(category=category)

    # backwards compatibility
    before_fork = before_fork_message

    def before_remove_contributor_message(self, node, removed):
        """Return warning text to display if removed contributor is the user
        who authorized the Dataverse addon
        """
        if self.user_settings and self.user_settings.owner == removed:
            category = node.project_or_component
            name = removed.fullname
            return ('The Dataverse add-on for this {category} is authenticated by {name}. '
                    'Removing this user will also remove write access to Dataverse '
                    'unless another contributor re-authenticates the add-on.'
                    ).format(**locals())

    # backwards compatibility
    before_remove_contributor = before_remove_contributor_message

    # Note: Registering Dataverse content is disabled for now
    # def after_register(self, node, registration, user, save=True):
    #     """After registering a node, copy the user settings and save the
    #     chosen folder.
    #
    #     :return: A tuple of the form (cloned_settings, message)
    #     """
    #     clone, message = super(AddonDataverseNodeSettings, self).after_register(
    #         node, registration, user, save=False
    #     )
    #     # Copy user_settings and add registration data
    #     if self.has_auth and self.folder is not None:
    #         clone.user_settings = self.user_settings
    #         clone.registration_data['folder'] = self.folder
    #     if save:
    #         clone.save()
    #     return clone, message

    def after_fork(self, node, fork, user, save=True):
        """After forking, copy user settings if the user is the one who authorized
        the addon.

        :return: A tuple of the form (cloned_settings, message)
        """
        clone, _ = super(AddonDataverseNodeSettings, self).after_fork(
            node=node, fork=fork, user=user, save=False
        )

        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = 'Dataverse authorization copied to fork.'
        else:
            message = ('Dataverse authorization not copied to fork. You may '
                        'authorize this fork on the <a href="{url}">Settings</a>'
                        'page.').format(url=fork.web_url_for('node_setting'))
        if save:
            clone.save()
        return clone, message

    def after_remove_contributor(self, node, removed):
        """If the removed contributor was the user who authorized the Dataverse
        addon, remove the auth credentials from this node.
        Return the message text that will be displayed to the user.
        """
        if self.user_settings and self.user_settings.owner == removed:
            self.user_settings = None
            self.save()
            name = removed.fullname
            url = node.web_url_for('node_setting')
            return ('Because the Dataverse add-on for this project was authenticated'
                    'by {name}, authentication information has been deleted. You '
                    'can re-authenticate on the <a href="{url}">Settings</a> page'
                    ).format(**locals())
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

    def clear(self, delete=False):
        """Clear settings and deauthorize any associated nodes.

        :param bool delete: Indicates if the settings should be deleted.
        """
        self.dataverse_username = None
        self.dataverse_password = None
        for node_settings in self.addondataversenodesettings__authorized:
            if delete:
                node_settings.delete(save=False)
            node_settings.deauthorize(Auth(self.owner))
            node_settings.save()
        return self

    def delete(self):
        super(AddonDataverseUserSettings, self).delete()
        self.clear(delete=True)

    def to_json(self, user):
        rv = super(AddonDataverseUserSettings, self).to_json(user)

        connection = connect(
            self.dataverse_username,
            self.dataverse_password,
        )

        rv.update({
            'authorized': connection is not None,
            'authorized_dataverse_user': self.dataverse_username or '',
            'show_submit': True,
        })
        return rv


class AddonDataverseNodeSettings(AddonNodeSettingsBase):

    dataverse_alias = fields.StringField()
    dataverse = fields.StringField()
    study_hdl = fields.StringField()
    study = fields.StringField()

    user_settings = fields.ForeignField(
        'addondataverseusersettings', backref='authorized'
    )

    def deauthorize(self, auth):
        """Remove user authorization from this node and log the event."""
        self.dataverse_alias = None
        self.dataverse = None
        self.study_hdl = None
        self.study = None
        self.user_settings = None

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
        authorized = (self.user_settings is not None and
            user_settings == self.user_settings)

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

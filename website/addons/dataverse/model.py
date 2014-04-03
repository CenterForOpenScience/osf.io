"""

"""

import os

from framework import fields
from website.addons.base import AddonNodeSettingsBase, AddonUserSettingsBase
from website.addons.dataverse.dvn.connection import DvnConnection
from website.addons.dataverse.config import TEST_CERT, HOST


def connect(username, password, host=HOST):
    connection = DvnConnection(
        username=username,
        password=password,
        host=host,
        cert=TEST_CERT,
    )
    return connection if connection.connected else None


class AddonDataverseUserSettings(AddonUserSettingsBase):

    dataverse_username = fields.StringField()
    dataverse_password = fields.StringField()

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

    dataverse_username = fields.StringField()
    dataverse_password = fields.StringField()
    #TODO: Replace dataverse number with alias (unique)
    dataverse_number = fields.IntegerField(default=0)
    dataverse = fields.StringField()
    study_hdl = fields.StringField()
    study = fields.StringField()
    user = fields.ForeignField('user')

    user_settings = fields.ForeignField(
        'addondataverseusersettings', backref='authorized'
    )

    def unauthorize(self):
        self.dataverse_username = None
        self.dataverse_password = None
        self.dataverse_number = 0
        self.dataverse = None
        self.study_hdl = None
        self.study = None
        self.user = None
        self.save()

    def to_json(self, user):

        dataverse_user = user.get_addon('dataverse')

        user_connection = connect(
            dataverse_user.dataverse_username,
            dataverse_user.dataverse_password,
        )

        rv = super(AddonDataverseNodeSettings, self).to_json(user)
        rv.update({
                'connected': False,
                'show_submit': False,
                'user_dataverse_account': dataverse_user.dataverse_username,
                'user_dataverse_connected': user_connection,
                'authorized_dataverse_user': self.dataverse_username,
                'authorized_user_name': self.user.fullname if self.user else '',
                'authorized_user_url': self.user.absolute_url if self.user else '',
        })

        connection = connect(
            self.dataverse_username,
            self.dataverse_password,
        )

        if connection is not None:

            # Check authorization
            authorized = dataverse_user.dataverse_username == self.dataverse_username

            # Get list of dataverses and studies
            dataverses = connection.get_dataverses() or []
            dataverse = dataverses[self.dataverse_number]
            studies = dataverse.get_studies() if dataverse else []

            rv.update({
                'connected': True,
                'authorized': authorized,
                'dataverses': [d.title for d in dataverses],
                'dataverse': self.dataverse or '',
                'dataverse_number': self.dataverse_number,
                'studies': [s.get_id() for s in studies],
                'study_names': [s.get_title() for s in studies],
                'study': self.study,
                'study_hdl': self.study_hdl,
            })

            if self.study_hdl is not None:

                study = dataverse.get_study_by_hdl(self.study_hdl)
                rv.update({
                    'dataverse_url': os.path.join('http://', HOST, 'dvn', 'dv', dataverse.alias),
                    'study_url': os.path.join('http://', HOST, 'dvn', 'dv', dataverse.alias,
                                              'faces', 'study', 'StudyPage.xhtml?globalId=' +
                                              study.doi),
                })

        return rv

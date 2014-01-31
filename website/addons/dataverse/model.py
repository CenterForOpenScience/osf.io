"""

"""

from framework import fields
from website.addons.base import AddonNodeSettingsBase, AddonUserSettingsBase
from website.addons.dataverse.dvn.connection import DvnConnection
from website.addons.dataverse.config import TEST_CERT, TEST_HOST


class AddonDataverseUserSettings(AddonUserSettingsBase):

    dataverse_username = fields.StringField()
    dataverse_password = fields.StringField()

    def connect(self, username, password, host=TEST_HOST):
        connection = DvnConnection(
            username=username,
            password=password,
            host=host,
            cert=TEST_CERT,
        )
        try:
            connection.get_dataverses()
            return connection
        except:
            return None


    def to_json(self, user):
        rv = super(AddonDataverseUserSettings, self).to_json(user)
        rv.update({
            'connection': self.connection or '',
            'authorized': self.dataverse_username is not None,
            'authorized_dataverse_user': self.dataverse_username if self.dataverse_username else '',
            'show_submit': True,
        })
        return rv


class AddonDataverseNodeSettings(AddonNodeSettingsBase):

    dataverse_number = fields.IntegerField(default=0)
    study_hdl = fields.StringField(default="None")
    user = fields.StringField()

    user_settings = fields.ForeignField(
        'addondataverseusersettings', backref='authorized'
    )

    def to_json(self, user):
        dataverse_user = user.get_addon('dataverse')
        connection = dataverse_user.connect(
            dataverse_user.dataverse_username,
            dataverse_user.dataverse_password
        )
        rv = super(AddonDataverseNodeSettings, self).to_json(user)
        rv.update({
            'connected': connection is not None,
        })

        #Define dataverse fields
        dataverses = connection.get_dataverses() or []
        dataverse = dataverses[int(self.dataverse_number)] if dataverses else None
        studies = dataverse.get_studies() if dataverse else []
        study = dataverse.get_study_by_hdl(self.study_hdl) if 'hdl' in self.study_hdl else None
        files = study.get_files() if study else []

        if connection is not None:
            rv.update({
                'dataverses': [d.collection.title for d in dataverses],
                'dataverse_number': self.dataverse_number,
                'studies': [s.get_id() for s in studies],
                'study_names': [s.get_title() for s in studies],
                'study_hdl': self.study_hdl,
                'files': [f.name for f in files],
                'show_submit': False #'hdl' in self.study_hdl
            })
        return rv

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
            'authorized': self.dataverse_username is not None,
            'authorized_dataverse_user': self.dataverse_username or '',
            'show_submit': True,
        })
        return rv


class AddonDataverseNodeSettings(AddonNodeSettingsBase):

    dataverse_username = fields.StringField()
    dataverse_password = fields.StringField()
    dataverse_number = fields.IntegerField(default=0)
    study_hdl = fields.StringField(default="None")
    user = fields.ForeignField('user')

    user_settings = fields.ForeignField(
        'addondataverseusersettings', backref='authorized'
    )

    def to_json(self, user):
        dataverse_user = user.get_addon('dataverse')
        rv = super(AddonDataverseNodeSettings, self).to_json(user)
        rv.update({
                'connected': False,
                'authorized_dataverse_user': self.dataverse_username,
                'authorized_user_name': self.user.fullname if self.user else '',
                'authorized_user_id': self.user._id if self.user else '',
        })

        connection = dataverse_user.connect(
            self.dataverse_username,
            self.dataverse_password,
        )

        if connection is not None:

            #Define dataverse fields
            dataverses = connection.get_dataverses() or []
            dataverse = dataverses[int(self.dataverse_number)] if dataverses else None
            studies = dataverse.get_studies() if dataverse else []
            study = dataverse.get_study_by_hdl(self.study_hdl) if dataverse and 'hdl' in self.study_hdl else None
            #files = study.get_files() if study else []

            rv.update({
                'connected': True,
                'authorized': dataverse_user.dataverse_username == self.dataverse_username,
                'dataverses': [d.collection.title for d in dataverses],
                'dataverse': dataverse.collection.title if dataverse else '',
                'dataverse_number': self.dataverse_number,
                'studies': [s.get_id() for s in studies],
                'study_names': [s.get_title() for s in studies],
                'study': study.get_title() if study else "None",
                'study_hdl': self.study_hdl,
                # 'files': [f.name for f in files],
                'show_submit': False #'hdl' in self.study_hdl
            })
        return rv

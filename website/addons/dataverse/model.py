"""

"""

from framework import fields
from website.addons.base import AddonNodeSettingsBase, AddonUserSettingsBase
from website.addons.dataverse.dvn.connection import DvnConnection
from website.addons.dataverse.config import TEST_CERT, HOST


class AddonDataverseUserSettings(AddonUserSettingsBase):

    dataverse_username = fields.StringField()
    dataverse_password = fields.StringField()

    def connect(self, username, password, host=HOST):
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
    dataverse = fields.StringField()
    study_hdl = fields.StringField()
    study = fields.StringField()
    user = fields.ForeignField('user')

    user_settings = fields.ForeignField(
        'addondataverseusersettings', backref='authorized'
    )

    def to_json(self, user):
        dataverse_user = user.get_addon('dataverse')
        rv = super(AddonDataverseNodeSettings, self).to_json(user)
        rv.update({
                'connected': False,
                'user_dataverse_account': user.get_addon('dataverse').dataverse_username,
                'authorized_dataverse_user': self.dataverse_username,
                'authorized_user_name': self.user.fullname if self.user else '',
                'authorized_user_id': self.user._id if self.user else '',
        })

        connection = dataverse_user.connect(
            self.dataverse_username,
            self.dataverse_password,
        )

        if connection is not None:

            # Get list of dataverses and studies
            dataverses = connection.get_dataverses() or []
            studies = dataverses[int(self.dataverse_number)].get_studies() if dataverses else []
            #study = dataverse.get_study_by_hdl(self.study_hdl) if dataverse and self.study_hdl else None
            #files = study.get_files() if study else []

            rv.update({
                'connected': True,
                'authorized': dataverse_user.dataverse_username == self.dataverse_username,
                'dataverses': [d.collection.title for d in dataverses],
                'dataverse': self.dataverse or '',
                'dataverse_number': self.dataverse_number,
                'studies': [s.get_id() for s in studies],
                'study_names': [s.get_title() for s in studies],
                'study': self.study,
                'study_hdl': self.study_hdl,
                # 'files': [f.name for f in files],
                'show_submit': False #'hdl' in self.study_hdl
            })
        return rv

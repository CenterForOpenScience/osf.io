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
            'connected': False,
        })

        #Define important fields
        dataverses = [] if len(connection.get_dataverses()) == 0 \
            else [dataverse.collection.title for dataverse in connection.get_dataverses()]
        studies = [] if len(dataverses) == 0 or len(connection.get_dataverses()[int(self.dataverse_number)].get_studies()) == 0\
            else [study.get_id() for study in connection.get_dataverses()[int(self.dataverse_number)].get_studies()]

        # if 'hdl' in self.study_hdl:
        #     files = [f.name for f in connection.get_dataverses()[int(self.dataverse_number)].get_study_by_hdl(self.study_hdl).get_files()] \
        #     if len(connection.get_dataverses()[int(self.dataverse_number)].get_study_by_hdl(self.study_hdl).get_files()) > 0 else []

        if connection is not None:
            rv.update({
                'connected': True,
                'dataverses': dataverses,
                'dataverse_number': self.dataverse_number or 0,
                'studies': studies,
                'study_hdl': self.study_hdl or "None",
                'show_submit': False #'hdl' in self.study_hdl
            })
        return rv

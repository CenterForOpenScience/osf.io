# encoding: utf-8
import os
import mock
import pytest
import datetime
import responses

from website.settings import USA
from api_tests.utils import create_test_file
from osf.models import QuickFilesNode

from osf_tests.factories import (
    AuthUserFactory,
    RegionFactory,
    ProjectFactory,
    RegistrationFactory,
    PreprintFactory
)

from osf.management.commands.international_user_metrics import (
    create_csv_header,
    append_to_csv,
    get_or_create_file,
    get_user_count_by_region,
    update_international_users_counts
)

from osf.management.commands.data_storage_usage import (
    get_node_count_by_region,
    get_registrations_count_by_region,
    get_preprint_count_by_region,
    get_quickfile_count_by_region
)

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestInternationalStorageMetrics:

    @pytest.fixture()
    def base_folder_response(self):
        with open(os.path.join(HERE, 'fixtures/get_or_create_csv_base_folder_response.json'), 'rb') as fp:
            return fp.read()

    @pytest.fixture()
    def create_csv_response(self):
        with open(os.path.join(HERE, 'fixtures/create_csv_response.json'), 'rb') as fp:
            return fp.read()

    @pytest.fixture()
    def get_csv_response(self):
        with open(os.path.join(HERE, 'fixtures/get_csv_response.json'), 'rb') as fp:
            return fp.read()

    @pytest.fixture()
    def create_csv_upload_response(self):
        with open(os.path.join(HERE, 'fixtures/create_csv_upload_response.json'), 'rb') as fp:
            return fp.read()

    @pytest.fixture()
    def region(self):
        return RegionFactory(name=USA)

    @pytest.fixture()
    def user(self, region):
        user = AuthUserFactory()
        usersettings = user.get_addon('osfstorage')
        usersettings.default_region = region
        usersettings.save()
        quickfile = QuickFilesNode.objects.filter(creator=user).first()
        create_test_file(quickfile, user)
        return user

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def registration(self, user):
        return RegistrationFactory(creator=user)

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    def test_get_user_count_by_region(self, user):
        assert get_user_count_by_region(USA) == 1

    def test_get_node_count_by_region(self, user, node):
        assert get_node_count_by_region(USA) == 1

    def test_get_registration_count_by_region(self, user, registration):
        assert get_registrations_count_by_region(USA) == 1

    def test_get_preprint_count_by_region(self, user, preprint):
        assert get_preprint_count_by_region(USA) == 1

    @pytest.mark.enable_quickfiles_creation
    def test_get_quickfile_count_by_region(self, user):
        assert get_quickfile_count_by_region(USA) == 1

    def test_create_csv_header(self):
        data = create_csv_header(['Fletcher Cox', 'Jason Peters', 'Darren Sproles'])
        assert data == 'Fletcher Cox,Jason Peters,Darren Sproles\r\n'

    @responses.activate
    def test_append_to_csv(self):
        data = [{
            'TDs': '9001',
            'INTs': '0'
        }]
        upload_link = 'http://fake.upload.link'

        responses.add(
            responses.Response(
                responses.GET,
                upload_link,
                body='TDs,INTs\r\n'
            ),
        )
        responses.add(
            responses.Response(
                responses.PUT,
                upload_link,
            ),
        )

        append_to_csv(upload_link, data, 'fake token')

        assert responses.calls[1].request.body == 'TDs,INTs\r\n9001,0\r\n'

    @responses.activate
    def test_create_file(self, base_folder_response, create_csv_response, create_csv_upload_response):
        base_folder_link = 'http://fake.folder.link'

        responses.add(
            responses.Response(
                responses.GET,
                base_folder_link,
                body=base_folder_response
            ),
        )
        responses.add(
            responses.Response(
                responses.GET,
                'http://localhost:8000/v2/nodes/fdx7t/files/osfstorage/5dfa59bd68c81e0cd373cea5/',
                body=create_csv_response
            ),
        )
        responses.add(
            responses.Response(
                responses.PUT,
                'http://localhost:7777/v1/resources/fdx7t/providers/osfstorage/5dfa59bd68c81e0cd373cea5/'
                '?name=TD-receptions-in-SB-by-QB.csv&kind=file',
                body=create_csv_upload_response
            ),
        )

        link = get_or_create_file(base_folder_link, 'TD-receptions-in-SB-by-QB.csv', 'fake token', b'["Foles", "Brady"]')
        assert link == 'http://localhost:7777/v1/resources/fdx7t/providers/osfstorage/5dfa5dee68c81e0d7e522848' \
                       '?kind=file'

    @responses.activate
    def test_get_file(self, base_folder_response, get_csv_response):
        base_folder_link = 'http://fake.folder.link'

        responses.add(
            responses.Response(
                responses.GET,
                base_folder_link,
                body=base_folder_response
            ),
        )
        responses.add(
            responses.Response(
                responses.GET,
                'http://localhost:8000/v2/nodes/fdx7t/files/osfstorage/5dfa59bd68c81e0cd373cea5/',
                body=get_csv_response
            ),
        )
        link = get_or_create_file(base_folder_link, 'TD-receptions-in-SB-by-QB.csv', 'fake token', b'["Foles", "Brady"]')
        assert link == 'http://localhost:7777/v1/resources/fdx7t/providers/osfstorage/5dfa607b68c81e0de2f53cc7'

    @mock.patch('osf.management.commands.international_user_metrics.get_or_create_file', return_value='fake.com')
    @mock.patch('osf.management.commands.international_user_metrics.append_to_csv')
    @mock.patch('osf.management.commands.international_user_metrics.DS_METRICS_OSF_TOKEN', 'fake-token')
    @mock.patch('osf.management.commands.international_user_metrics.DS_METRICS_BASE_FOLDER', 'base-folder')
    def test_update_international_users_counts(self, mock_get_or_create_file, mock_append_to_csv):
        update_international_users_counts(dry_run=False)

        date = datetime.datetime.now().strftime('%Y-%m-%d')

        mock_get_or_create_file.assert_called_with('fake.com',
                                                   [{'date': date,
                                                     'users_australia_storage': 0,
                                                     'users_usa_storage': 0,
                                                     'users_germany_storage': 0,
                                                     'users_canada_storage': 0}],
                                                   'fake-token'
                                                   )

        mock_append_to_csv.assert_called_with('base-folder',
                                              'osf_international_user_metrics.csv',
                                              'fake-token',
                                              'date,users_usa_storage,users_germany_storage,users_canada_storage,users_australia_storage\r\n'
                                              )

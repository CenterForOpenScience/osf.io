import json
from nose import tools as nt

from django.test import RequestFactory

from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory


from admin.rdm_metadata import views
from admin.rdm_metadata import erad
from admin_tests.utilities import setup_user_view


class TestDashboard(AdminTestCase):
    def setUp(self):
        super(TestDashboard, self).setUp()
        self.user = AuthUserFactory()
        self.request_url = '/metadata/erad/'

    def test_super_admin_get(self, *args, **kwargs):
        request = RequestFactory().get(self.request_url)
        view = views.ERadRecordDashboard()
        view = setup_user_view(view, request, user=self.user)
        self.user.is_superuser = True
        self.user.is_staff = False
        res = view.get(request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)
        nt.assert_equal(res.context_data, {})

class TestRecords(AdminTestCase):
    def setUp(self):
        super(TestRecords, self).setUp()
        self.user = AuthUserFactory()
        self.request_url = '/metadata/erad/records'

    def test_post_empty_data(self, *args, **kwargs):
        request = RequestFactory().post(
            self.request_url,
            data=json.dumps([]),
            content_type='application/json',
        )
        view = views.ERadRecords()
        view = setup_user_view(view, request, user=self.user)
        res = view.post(request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)
        nt.assert_equal(res.content, b'{"status": "OK", "records": 0}')

    def test_post_some_data(self, *args, **kwargs):
        data = '\t'.join(erad.ERAD_COLUMNS) + '\n'
        for row in range(10):
            data += '\t'.join(['value{}-{}'.format(row, i) if col != 'NENDO' else '2022'
                               for i, col in enumerate(erad.ERAD_COLUMNS)]) + '\n'
        request = RequestFactory().post(
            self.request_url,
            data=json.dumps(
                [
                    {
                        'name': 'valid_data.tsv',
                        'text': data,
                    },
                ]
            ),
            content_type='application/json',
        )
        view = views.ERadRecords()
        view = setup_user_view(view, request, user=self.user)
        res = view.post(request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)
        nt.assert_equal(res.content, b'{"status": "OK", "records": 10}')

    def test_post_bad_data(self, *args, **kwargs):
        request = RequestFactory().post(
            self.request_url,
            data=json.dumps(
                [
                    {
                        'name': 'bad_data.tsv',
                        'text': 'TEST1\tTEST2\ntest1\ttest2\n',
                    },
                ]
            ),
            content_type='application/json',
        )
        view = views.ERadRecords()
        view = setup_user_view(view, request, user=self.user)
        res = view.post(request, *args, **kwargs)
        nt.assert_equal(res.status_code, 400)
        nt.assert_equal(
            res.content,
            b'{"status": "error", "message": "Column \\"KENKYUSHA_NO\\" not exists (record=0)"}'
        )

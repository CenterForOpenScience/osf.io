from unittest import mock
import pytest
import datetime
import responses

from django.utils import timezone
from osf.utils.permissions import READ
from api.base.settings.defaults import API_BASE
from api_tests import utils as test_utils
from framework.auth.core import Auth
from osf.models import (
    NodeLicense,
    PreprintContributor,
    PreprintLog
)
from osf.utils import permissions as osf_permissions
from osf.utils.permissions import WRITE
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    ProjectFactory,
    SubjectFactory,
)
from website.settings import CROSSREF_URL


def build_preprint_update_payload(node_id, attributes=None, relationships=None, jsonapi_type='preprints'):
    payload = {
        'data': {
            'id': node_id,
            'type': jsonapi_type,
            'attributes': attributes,
            'relationships': relationships
        }
    }
    return payload

@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestPreprintUpdate:

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/'

    @pytest.fixture()
    def subject(self):
        return SubjectFactory()

    def test_update_original_publication_date_to_none(self, app, user, preprint, url):
        # Original pub date accidentally set, need to remove
        write_contrib = AuthUserFactory()
        preprint.add_contributor(write_contrib, WRITE, save=True)
        preprint.original_publication_date = '2013-12-11 10:09:08.070605+00:00'
        preprint.save()
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'original_publication_date': None,
            }
        )

        res = app.patch_json_api(
            url,
            update_payload,
            auth=write_contrib.auth,
        )

        assert res.status_code == 200
        preprint.reload()
        assert preprint.original_publication_date is None

    def test_update_custom_publication_citation_to_none(self, app, preprint, url):
        write_contrib = AuthUserFactory()
        preprint.add_contributor(write_contrib, WRITE, save=True)
        preprint.custom_publication_citation = 'fake citation'
        preprint.save()
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'custom_publication_citation': None}
        )
        res = app.patch_json_api(url, update_payload, auth=write_contrib.auth)
        assert res.status_code == 200
        preprint.reload()
        assert preprint.custom_publication_citation is None

    @responses.activate
    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated', mock.Mock())
    def test_update_preprint_permission_write_contrib(self, app, preprint, url):
        responses.add(
            responses.Response(
                responses.POST,
                CROSSREF_URL,
                content_type='text/html;charset=ISO-8859-1',
                status=200,
            ),
        )
        write_contrib = AuthUserFactory()
        preprint.add_contributor(write_contrib, WRITE, save=True)

        doi = '10.123/456/789'
        original_publication_date = '2013-12-11 10:09:08.070605+00:00'
        license_record = {
            'year': '2015',
            'copyright_holders': ['Tonya Bateman']
        }
        license = NodeLicense.objects.filter(name='No license').first()
        title = 'My Preprint Title'
        description = 'My Preprint Description'
        tags = ['test tag']
        node = ProjectFactory(creator=write_contrib)
        new_file = test_utils.create_test_preprint_file(
            preprint,
            write_contrib,
            filename='shook_that_mans_hand.pdf'
        )

        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'original_publication_date': original_publication_date,
                'doi': doi,
                'license_record': license_record,
                'title': title,
                'description': description,
                'tags': tags,
            },
            relationships={
                'node': {
                    'data': {
                        'type': 'nodes', 'id': node._id
                    }
                },
                'primary_file': {
                    'data': {
                        'type': 'file',
                        'id': new_file._id
                    }
                },
                'license': {
                    'data': {
                        'type': 'licenses',
                        'id': license._id
                    }
                }
            }
        )

        res = app.patch_json_api(
            url,
            update_payload,
            auth=write_contrib.auth,
        )

        assert res.status_code == 200
        preprint.reload()

        assert preprint.article_doi == doi
        assert str(preprint.original_publication_date) == original_publication_date
        assert preprint.license.node_license == license
        assert preprint.license.year == license_record['year']
        assert preprint.license.copyright_holders == license_record['copyright_holders']
        assert preprint.title == title
        assert preprint.description == description
        assert preprint.tags.first().name == tags[0]
        assert preprint.node == node
        assert preprint.primary_file == new_file

    def test_update_published_write_contrib(self, app, preprint, url):
        preprint.is_published = False
        preprint.save()

        write_contrib = AuthUserFactory()
        preprint.add_contributor(write_contrib, WRITE, save=True)

        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'is_published': 'true'}
        )

        res = app.patch_json_api(
            url,
            update_payload,
            auth=write_contrib.auth,
            expect_errors=True
        )

        assert res.status_code == 403
        assert preprint.is_published is False

    def test_update_node(self, app, user, preprint, url):
        assert preprint.node is None
        node = ProjectFactory(creator=user)
        update_node_payload = build_preprint_update_payload(
            preprint._id,
            relationships={
                'node': {
                    'data': {
                        'type': 'nodes',
                        'id': node._id
                    }
                }
            }
        )

        res = app.patch_json_api(url, update_node_payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['relationships']['node']['data']['id'] == node._id
        preprint.reload()
        assert preprint.node == node

    def test_update_node_permissions(self, app, user, preprint, url):
        assert preprint.node is None
        node = ProjectFactory()
        update_node_payload = build_preprint_update_payload(
            preprint._id,
            relationships={
                'node': {
                    'data': {
                        'type': 'nodes', 'id': node._id
                    }
                }
            }
        )

        res = app.patch_json_api(url, update_node_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 403
        preprint.reload()
        assert preprint.node is None

    def test_update_node_existing_preprint(self, app, user, preprint, url):
        assert preprint.node is None
        node = ProjectFactory(creator=user)
        # Create preprint with same provider on node
        PreprintFactory(creator=user, project=node, provider=preprint.provider)
        update_node_payload = build_preprint_update_payload(
            preprint._id,
            relationships={
                'node': {
                    'data': {
                        'type': 'nodes', 'id': node._id
                    }
                }
            }
        )

        res = app.patch_json_api(url, update_node_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        preprint.reload()
        assert preprint.node == node

    def test_update_deleted_node(self, app, user, preprint, url):
        assert preprint.node is None
        node = ProjectFactory(creator=user)
        node.is_deleted = True
        node.save()
        update_node_payload = build_preprint_update_payload(
            preprint._id,
            relationships={
                'node': {
                    'data': {
                        'type': 'nodes',
                        'id': node._id
                    }
                }
            }
        )

        res = app.patch_json_api(url, update_node_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Cannot attach a deleted project to a preprint.'
        preprint.reload()
        assert preprint.node is None

    def test_update_primary_file(self, app, user, preprint, url):
        new_file = test_utils.create_test_preprint_file(
            preprint,
            user,
            filename='shook_that_mans_hand.pdf'
        )
        relationships = {
            'primary_file': {
                'data': {
                    'type': 'file',
                    'id': new_file._id
                }
            }
        }
        assert preprint.primary_file != new_file
        update_file_payload = build_preprint_update_payload(preprint._id, relationships=relationships)

        res = app.patch_json_api(url, update_file_payload, auth=user.auth)
        assert res.status_code == 200

        preprint.reload()
        assert preprint.primary_file == new_file

        log = preprint.logs.latest()
        assert log.action == 'file_updated'
        assert log.params.get('preprint') == preprint._id

    def test_update_preprints_with_none_type(self, app, user, preprint, url):
        res = app.patch_json_api(
            url,
            {
                'data': {
                    'id': preprint._id,
                    'type': None,
                    'attributes': None,
                    'relationship': None
                }
            },
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    def test_update_preprints_with_no_type(self, app, user, preprint, url):
        res = app.patch_json_api(
            url,
            {
                'data': {
                    'id': preprint._id,
                    'attributes': None,
                    'relationship': None
                }
            },
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    def test_update_preprints_with_wrong_type(self, app, user, preprint, url):
        res = app.patch_json_api(
            url,
            build_preprint_update_payload(preprint._id, jsonapi_type='Nonsense'),
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    def test_new_primary_not_in_node(self, app, user, preprint, url):
        project = ProjectFactory()
        file_for_project = test_utils.create_test_file(
            project,
            user,
            filename='six_pack_novak.pdf'
        )

        relationships = {
            'primary_file': {
                'data': {
                    'type': 'file',
                    'id': file_for_project._id
                }
            }
        }

        update_file_payload = build_preprint_update_payload(
            preprint._id,
            relationships=relationships
        )

        res = app.patch_json_api(
            url,
            update_file_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400

        preprint.reload()
        assert preprint.primary_file != file_for_project

    def test_update_original_publication_date(self, app, user, preprint, url):
        date = timezone.now() - datetime.timedelta(days=365)
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'original_publication_date': str(date)}
        )
        res = app.patch_json_api(url, update_payload, auth=user.auth)
        assert res.status_code == 200

        preprint.reload()
        assert preprint.original_publication_date == date

    def test_update_custom_publication_citation(self, app, user, preprint, url):
        citation = 'fake citation'
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'custom_publication_citation': citation}
        )
        res = app.patch_json_api(url, update_payload, auth=user.auth)
        assert res.status_code == 200
        preprint.reload()
        assert preprint.custom_publication_citation == citation

    def test_title_has_a_512_char_limit(self, app, user, preprint, url):
        new_title = 'a' * 513
        update_title_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'title': new_title,
            }
        )
        res = app.patch_json_api(
            url,
            update_title_payload,
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Ensure this field has no more than 512 characters.'
        preprint.reload()
        assert preprint.title != new_title

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_update_description_and_title(
            self,
            mock_preprint_updated,
            app,
            user,
            preprint,
            url
    ):
        new_title = 'Brother Nero'
        new_description = 'I knew you\'d come!'
        assert preprint.description != new_description
        assert preprint.title != new_title
        update_title_description_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'title': new_title,
                'description': new_description,
            }
        )
        res = app.patch_json_api(
            url,
            update_title_description_payload,
            auth=user.auth)

        assert res.status_code == 200
        preprint.reload()

        assert preprint.description == new_description
        assert preprint.title == new_title
        assert mock_preprint_updated.called

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_update_tags(self, mock_update_doi_metadata, app, user, preprint, url):
        new_tags = ['hey', 'sup']

        for tag in new_tags:
            assert tag not in preprint.tags.all().values_list('name', flat=True)

        update_tags_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'tags': new_tags
            }
        )
        res = app.patch_json_api(url, update_tags_payload, auth=user.auth)

        assert res.status_code == 200
        preprint.reload()

        assert sorted(
            list(
                preprint.tags.all().values_list(
                    'name',
                    flat=True))
        ) == new_tags
        assert mock_update_doi_metadata.called

        # No tags
        update_tags_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'tags': []
            }
        )
        res = app.patch_json_api(url, update_tags_payload, auth=user.auth)

        assert res.status_code == 200
        preprint.reload()
        assert preprint.tags.count() == 0

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_update_contributors(
            self, mock_update_doi_metadata, app, user, preprint, url
    ):
        new_user = AuthUserFactory()
        res = app.post_json_api(
            url + 'contributors/',
            {
                'data': {
                    'attributes': {
                        'bibliographic': True,
                        'permission': WRITE,
                        'send_email': False
                    },
                    'type': 'contributors',
                    'relationships': {
                        'users': {
                            'data': {
                                'id': new_user._id,
                                'type': 'users'
                            }
                        }
                    }
                }
            },
            auth=user.auth
        )

        assert res.status_code == 201
        assert new_user in preprint.contributors
        assert preprint.has_permission(new_user, WRITE)
        assert PreprintContributor.objects.get(preprint=preprint, user=new_user).visible is True
        assert mock_update_doi_metadata.called

    def test_write_contrib_can_attempt_to_set_primary_file(self, app, user, preprint, url):
        preprint.node = None
        preprint.save()
        read_write_contrib = AuthUserFactory()
        preprint.add_contributor(
            read_write_contrib,
            permissions=WRITE,
            auth=Auth(user),
            save=True
        )
        new_file = test_utils.create_test_preprint_file(
            preprint,
            user,
            filename='lovechild_reason.pdf'
        )

        res = app.patch_json_api(
            url,
            {
                'data': {
                    'type': 'preprints',
                    'id': preprint._id,
                    'attributes': {},
                    'relationships': {
                        'primary_file': {
                            'data': {
                                'type': 'file',
                                'id': new_file._id
                            }
                        }
                    }
                }
            },
            auth=read_write_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 200

    def test_noncontrib_cannot_set_primary_file(self, app, user, preprint, url):
        non_contrib = AuthUserFactory()
        new_file = test_utils.create_test_preprint_file(
            preprint,
            user,
            filename='flowerchild_nik.pdf'
        )

        res = app.patch_json_api(
            url,
            {
                'data': {
                    'type': 'preprints',
                    'id': preprint._id,
                    'attributes': {},
                    'relationships': {
                        'primary_file': {
                            'data': {
                                'type': 'file',
                                'id': new_file._id
                            }
                        }
                    }
                }
            },
            auth=non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_update_published(self, app, user):
        unpublished = PreprintFactory(creator=user, is_published=False)
        app.patch_json_api(
            f'/{API_BASE}preprints/{unpublished._id}/',
            build_preprint_update_payload(
                unpublished._id,
                attributes={'is_published': True}
            ),
            auth=user.auth
        )
        unpublished.reload()
        assert unpublished.is_published

    def test_update_published_does_not_make_node_public(self, app, user):
        project = ProjectFactory(creator=user)
        unpublished = PreprintFactory(
            creator=user,
            is_published=False,
            project=project
        )
        assert not unpublished.node.is_public
        app.patch_json_api(
            f'/{API_BASE}preprints/{unpublished._id}/',
            build_preprint_update_payload(
                unpublished._id,
                attributes={'is_published': True}),
            auth=user.auth
        )
        unpublished.node.reload()
        unpublished.reload()

        assert unpublished.node.is_public is False
        assert unpublished.is_public

    def test_update_has_coi(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'has_coi': True}
        )

        contrib = AuthUserFactory()
        preprint.add_contributor(contrib, READ)
        res = app.patch_json_api(
            url,
            update_payload,
            auth=contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['has_coi']

        preprint.reload()
        assert preprint.has_coi
        log = preprint.logs.first()
        assert log.action == PreprintLog.UPDATE_HAS_COI
        assert log.params == {'preprint': preprint._id, 'user': user._id, 'value': True}

    def test_update_conflict_of_interest_statement(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'conflict_of_interest_statement': 'Owns shares in Closed Science Corporation.'}
        )
        contrib = AuthUserFactory()
        preprint.add_contributor(contrib, READ)
        res = app.patch_json_api(
            url,
            update_payload,
            auth=contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

        preprint.has_coi = False
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Cannot provide conflict of interest statement when has_coi is set to False.'

        preprint.has_coi = True
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['conflict_of_interest_statement'] ==\
               'Owns shares in Closed Science Corporation.'

        preprint.reload()
        assert preprint.conflict_of_interest_statement == 'Owns shares in Closed Science Corporation.'
        log = preprint.logs.first()
        assert log.action == PreprintLog.UPDATE_COI_STATEMENT
        assert log.params == {
            'preprint': preprint._id,
            'user': user._id,
            'value': 'Owns shares in Closed Science Corporation.'
        }

    def test_update_has_data_links(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(preprint._id, attributes={'has_data_links': 'available'})

        contrib = AuthUserFactory()
        preprint.add_contributor(contrib, READ)
        res = app.patch_json_api(url, update_payload, auth=contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['has_data_links'] == 'available'

        preprint.reload()
        assert preprint.has_data_links
        log = preprint.logs.first()
        assert log.action == PreprintLog.UPDATE_HAS_DATA_LINKS
        assert log.params == {'value': 'available', 'user': user._id, 'preprint': preprint._id}

    def test_update_why_no_data(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(preprint._id, attributes={'why_no_data': 'My dog ate it.'})

        contrib = AuthUserFactory()
        preprint.add_contributor(contrib, READ)
        res = app.patch_json_api(url, update_payload, auth=contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You cannot edit this statement while your data links availability is set to true or is unanswered.'

        preprint.has_data_links = 'no'
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['why_no_data'] == 'My dog ate it.'

        preprint.reload()
        assert preprint.why_no_data
        log = preprint.logs.first()
        assert log.action == PreprintLog.UPDATE_WHY_NO_DATA
        assert log.params == {'user': user._id, 'preprint': preprint._id}

    def test_update_data_links(self, app, user, preprint, url):
        data_links = ['http://www.JasonKelce.com', 'http://www.ItsTheWholeTeam.com/']
        update_payload = build_preprint_update_payload(preprint._id, attributes={'data_links': data_links})

        contrib = AuthUserFactory()
        preprint.add_contributor(contrib, READ)
        res = app.patch_json_api(url, update_payload, auth=contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

        preprint.has_data_links = 'no'
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Cannot provide data links when has_data_links is set to "no".'

        preprint.has_data_links = 'available'
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['data_links'] == data_links

        preprint.reload()
        assert preprint.data_links == data_links
        log = preprint.logs.first()
        assert log.action == PreprintLog.UPDATE_DATA_LINKS
        assert log.params == {'user': user._id, 'preprint': preprint._id}

        update_payload = build_preprint_update_payload(preprint._id, attributes={'data_links': 'maformed payload'})
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "str".'

    def test_invalid_data_links(self, app, user, preprint, url):
        preprint.has_data_links = 'available'
        preprint.save()

        update_payload = build_preprint_update_payload(preprint._id, attributes={'data_links': ['thisaintright']})

        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Enter a valid URL.'

    def test_update_has_prereg_links(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(preprint._id, attributes={'has_prereg_links': 'available'})

        contrib = AuthUserFactory()
        preprint.add_contributor(contrib, READ)
        res = app.patch_json_api(url, update_payload, auth=contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['has_prereg_links'] == 'available'

        preprint.reload()
        assert preprint.has_prereg_links
        log = preprint.logs.first()
        assert log.action == PreprintLog.UPDATE_HAS_PREREG_LINKS
        assert log.params == {'value': 'available', 'user': user._id, 'preprint': preprint._id}

    def test_invalid_prereg_links(self, app, user, preprint, url):
        preprint.has_prereg_links = 'available'
        preprint.save()

        update_payload = build_preprint_update_payload(preprint._id, attributes={'prereg_links': ['thisaintright']})

        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Enter a valid URL.'

    def test_no_data_links_clears_links(self, app, user, preprint, url):
        preprint.has_data_links = 'available'
        preprint.data_links = ['http://www.apple.com']
        preprint.save()

        update_payload = build_preprint_update_payload(preprint._id, attributes={'has_data_links': 'no'})

        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['has_data_links'] == 'no'
        assert res.json['data']['attributes']['data_links'] == []

        preprint.reload()
        assert preprint.has_data_links == 'no'
        assert preprint.data_links == []

    def test_no_prereg_links_clears_links(self, app, user, preprint, url):
        preprint.has_prereg_links = 'available'
        preprint.prereg_links = ['http://example.com']
        preprint.prereg_link_info = 'prereg_analysis'
        preprint.save()

        update_payload = build_preprint_update_payload(preprint._id, attributes={'has_prereg_links': 'no'})

        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['has_prereg_links'] == 'no'
        preprint.reload()
        assert res.json['data']['attributes']['prereg_links'] == []
        assert not res.json['data']['attributes']['prereg_link_info']

        assert preprint.prereg_links == []
        assert preprint.prereg_link_info is None

    def test_update_why_no_prereg(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(preprint._id, attributes={'why_no_prereg': 'My dog ate it.'})

        contrib = AuthUserFactory()
        preprint.add_contributor(contrib, READ)
        res = app.patch_json_api(url, update_payload, auth=contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

        preprint.has_prereg_links = 'available'
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You cannot edit this statement while your prereg links availability is set to true or is unanswered.'

        update_payload = build_preprint_update_payload(preprint._id, attributes={
            'why_no_prereg': 'My dog ate it.',
            'has_prereg_links': 'no'
        })
        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['why_no_prereg'] == 'My dog ate it.'

        preprint.reload()
        assert preprint.why_no_prereg == 'My dog ate it.'

        log = preprint.logs.filter(action=PreprintLog.UPDATE_WHY_NO_PREREG).first()
        assert log is not None, 'Expected log entry for why_no_prereg_updated not found.'
        assert log.action == PreprintLog.UPDATE_WHY_NO_PREREG
        assert log.params == {'user': user._id, 'preprint': preprint._id}

    def test_update_prereg_links(self, app, user, preprint, url):

        prereg_links = ['http://www.JasonKelce.com', 'http://www.ItsTheWholeTeam.com/']
        update_payload = build_preprint_update_payload(preprint._id, attributes={'prereg_links': prereg_links})

        contrib = AuthUserFactory()
        preprint.add_contributor(contrib, READ)
        res = app.patch_json_api(url, update_payload, auth=contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

        preprint.has_prereg_links = 'no'
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You cannot edit this field while your prereg links availability is set to false or is unanswered.'

        preprint.has_prereg_links = 'available'
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['prereg_links'] == prereg_links

        preprint.reload()
        assert preprint.prereg_links == prereg_links
        log = preprint.logs.first()
        assert log.action == PreprintLog.UPDATE_PREREG_LINKS
        assert log.params == {'user': user._id, 'preprint': preprint._id}

        update_payload = build_preprint_update_payload(preprint._id, attributes={'prereg_links': 'maformed payload'})
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "str".'

    def test_update_prereg_link_info(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'prereg_link_info': 'prereg_designs'}
        )

        preprint.has_prereg_links = 'no'
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You cannot edit this field while your prereg links availability is set to false or is unanswered.'

        preprint.has_prereg_links = 'available'
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['prereg_link_info'] == 'prereg_designs'

        preprint.reload()
        assert preprint.prereg_link_info == 'prereg_designs'
        log = preprint.logs.first()
        assert log.action == PreprintLog.UPDATE_PREREG_LINKS_INFO
        assert log.params == {'user': user._id, 'preprint': preprint._id}

        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'prereg_link_info': 'maformed payload'}
        )
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '"maformed payload" is not a valid choice.'

    def test_update_has_coi_false_with_null_conflict_statement(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'has_coi': False,
                'conflict_of_interest_statement': None
            }
        )

        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['has_coi'] is False
        assert res.json['data']['attributes']['conflict_of_interest_statement'] is None

        preprint.reload()
        assert preprint.has_coi is False
        assert preprint.conflict_of_interest_statement is None

    def test_update_has_data_links_no_with_data_links_provided(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'has_data_links': 'no',
                'data_links': ['http://example.com/data']
            }
        )

        initial_has_data_links = preprint.has_data_links
        initial_data_links = preprint.data_links

        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Cannot provide data links when has_data_links is set to "no".'

        preprint.reload()

        assert preprint.has_data_links == initial_has_data_links
        assert preprint.data_links == initial_data_links

        assert preprint.has_data_links != 'no'

    def test_update_has_data_links_no_with_empty_data_links(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'has_data_links': 'no',
                'data_links': []
            }
        )

        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['has_data_links'] == 'no'
        assert res.json['data']['attributes']['data_links'] == []

        preprint.reload()
        assert preprint.has_data_links == 'no'
        assert preprint.data_links == []

    def test_update_has_prereg_links_no_with_empty_prereg_links(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'has_prereg_links': 'no',
                'prereg_links': [],
                'prereg_link_info': ''
            }
        )

        res = app.patch_json_api(url, update_payload, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['has_prereg_links'] == 'no'
        assert res.json['data']['attributes']['prereg_links'] == []
        assert res.json['data']['attributes']['prereg_link_info'] == ''

        preprint.reload()
        assert preprint.has_prereg_links == 'no'
        assert preprint.prereg_links == []
        assert preprint.prereg_link_info == ''

    def test_non_admin_cannot_update_has_coi(self, app, user, preprint, url):
        write_contrib = AuthUserFactory()
        preprint.add_contributor(write_contrib, permissions=osf_permissions.WRITE, auth=Auth(user), save=True)

        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'has_coi': True}
        )

        res = app.patch_json_api(url, update_payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'Must have admin permissions to update author assertion fields.'

        preprint.reload()
        assert preprint.has_coi is None

    def test_sloan_updates(self, app, user, preprint, url):
        """
        - Tests to ensure updating a preprint with unchanged data does not create superfluous log statements.
        - Tests to ensure various dependent fields can be updated in a single request.
        """
        preprint.has_prereg_links = 'available'
        preprint.prereg_links = ['http://no-sf.io']
        preprint.prereg_link_info = 'prereg_designs'
        preprint.save()

        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'has_prereg_links': 'available',
                'prereg_link_info': 'prereg_designs',
                'prereg_links': ['http://osf.io'],  # changing here should be only non-factory created log.
            }
        )
        app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        # Any superfluous log statements?
        logs = preprint.logs.all().values_list('action', 'params')
        assert logs.count() == 3  # actions should be: 'subjects_updated', 'published', 'prereg_links_updated'
        assert logs.latest() == ('prereg_links_updated', {'user': user._id, 'preprint': preprint._id})

        # Can we set `has_prereg_links` to false and update `why_no_prereg` in a single request?
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'has_prereg_links': 'no',
                'why_no_prereg': 'My dog ate it.'
            }
        )
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 200
        assert res.json['data']['attributes']['has_prereg_links'] == 'no'
        assert res.json['data']['attributes']['why_no_prereg'] == 'My dog ate it.'

        preprint.refresh_from_db()
        assert preprint.has_prereg_links == 'no'
        assert preprint.why_no_prereg == 'My dog ate it.'

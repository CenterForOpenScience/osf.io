import pytest

from osf.models import PreprintContributor
from osf.utils.permissions import WRITE, ADMIN
from osf_tests.factories import AuthUserFactory, PreprintFactory
from scripts.remove_after_use.fix_unmerged_preprints import main as fix_unmerged_preprints


pytestmark = pytest.mark.django_db


class TestFixUnmergedPreprints:

    @pytest.fixture()
    def merger(self):
        return AuthUserFactory()

    @pytest.fixture()
    def mergee(self, merger):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint_mergee_creator(self, mergee):
        return PreprintFactory(creator=mergee)

    @pytest.fixture()
    def preprint_with_contributor(self, mergee):
        preprint = PreprintFactory()
        preprint.add_contributor(mergee, permissions=WRITE, visible=False, save=True)
        preprint.save()
        return preprint

    @pytest.fixture()
    def preprint_with_merger_and_mergee(self, mergee, merger):
        preprint = PreprintFactory()
        preprint.add_contributor(mergee)
        preprint.add_contributor(merger)
        preprint.save()
        return preprint

    def test_main(self, merger, mergee, preprint_mergee_creator, preprint_with_contributor):
        mergee.merged_by = merger
        mergee.save()

        fix_unmerged_preprints()

        preprint_mergee_creator.reload()
        preprint_with_contributor.reload()
        assert merger == preprint_mergee_creator.creator
        assert merger in preprint_with_contributor.contributors.all()
        assert preprint_with_contributor.creator != merger
        assert preprint_with_contributor.creator in preprint_with_contributor.contributors.all()

        contrib_obj = PreprintContributor.objects.get(user=merger, preprint=preprint_mergee_creator)
        assert contrib_obj.visible
        assert contrib_obj.permission == ADMIN

        contrib_obj = PreprintContributor.objects.get(user=merger, preprint=preprint_with_contributor)
        assert not contrib_obj.visible
        assert contrib_obj.permission == WRITE

    def test_integrity_error(self, merger, mergee, preprint_mergee_creator, preprint_with_contributor, preprint_with_merger_and_mergee):
        """
        If both merger and mergee are contribs on the same project trying to add them to a preprint violates a unique
        constraint and throws an error
        """
        mergee.merged_by = merger
        mergee.save()

        fix_unmerged_preprints()

        preprint_mergee_creator.reload()
        preprint_with_contributor.reload()
        assert merger == preprint_mergee_creator.creator
        assert merger in preprint_with_contributor.contributors.all()
        assert preprint_with_contributor.creator != merger
        assert preprint_with_contributor.creator in preprint_with_contributor.contributors.all()

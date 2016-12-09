# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from nose.tools import assert_equal, ok_

from modularodm import Q
from framework.auth import Auth
from tests import factories
from tests.base import DbIsolationMixin
from tests.test_search import OsfTestCase
from tests.test_search.test_permissions.test_nodefuncs import (
    public_project, public_component_of_a_public_project
)
from tests.utils import mock_archive, run_celery_tasks
from website.addons.wiki.model import NodeWikiPage
from website.files.models.base import File
from website.project.model import Node


# The return value is: (search query, category, key to test, expected value).
# Check TestSearchSearchAPI for usage.

def base(node):
    category = 'project' if node.parent_node is None else 'component'
    return 'flim', category, 'title', 'Flim Flammity'


def file_on(node):
    node.get_addon('osfstorage').get_root().append_file('Blim Blammity')
    return 'blim', 'file', 'name', 'Blim Blammity'


def wiki_on(node):
    category = 'project' if node.parent_node is None else 'component'
    with run_celery_tasks():
        node.update_node_wiki('Blim Blammity', 'Blim, blammity.', Auth(node.creator))
    return 'blim', category, 'title', 'Flim Flammity'


# Registrations are more complicated, because they have multiple possible
# states. We therefore have a second-level generator to programmatically create
# the functions to vary a node according to the different registration states.

def _register(*a, **kw):
    embargo = kw.get('embargo')                         # (None, True, False)
    kw['embargo'] = False if embargo is None else True  # (True, False)
    for unwanted in ('regfunc', 'should_be_public', 'private', 'public'):
        kw.pop(unwanted, '')
    registration = mock_archive(*a, **kw).__enter__()  # gooooooofffyyyyyy
    if embargo is False and registration.is_embargoed:
        registration.terminate_embargo(Auth(registration.creator))
        registration.update_search()
    return 'flim', 'registration', 'title', 'Flim Flammity'


def name_regfunc(embargo, autoapprove, autocomplete, retraction, autoapprove_retraction, **_):
    retraction_part = '' if not retraction else \
                      '{}_retraction_of_'.format('approved' if autoapprove_retraction else
                                                    'unapproved')
    return '{}{}{}_{}_{}_registration_of_a'.format(
        retraction_part,
        '' if not retraction else 'an_' if embargo in (None, True) else 'a_',
        'embargoed' if embargo else 'unembargoed' if embargo is None else 'formerly_embargoed',
        'approved' if autoapprove else 'unapproved',
        'complete' if autocomplete else 'incomplete',
    ).encode('ascii')


def want_regfunc(name):  # helpful to filter regfuncs during development
    return True


def determine_whether_it_should_be_public(retraction, embargo, autoapprove_retraction, \
                                                                  autocomplete, autoapprove, **kw):
    if retraction and embargo:
        # Approving a retraction removes embargoes and makes the reg public,
        # but only for *completed* registrations.
        should_be_public = autoapprove_retraction and autocomplete
    elif embargo:
        should_be_public = False
    else:
        should_be_public = (autoapprove or autoapprove_retraction) and autocomplete
    return should_be_public


def create_regfunc(**kw):
    def regfunc(node):
        return _register(node, **kw)
    regfunc.__name__ = name_regfunc(**kw)
    return regfunc


def create_regfuncs():
    public = set()
    private = set()
    # Default values are listed first for all of these ...
    for embargo in (None, True, False):  # never, currently, formerly
        for autoapprove in (False, True):
            for autocomplete in (True, False):
                for autoapprove_retraction in (None, False, True):
                    retraction = autoapprove_retraction is not None
                    if retraction and not (autoapprove or embargo is not None):
                        continue  # 'Only public or embargoed registrations may be withdrawn.'
                    regfunc = create_regfunc(**locals())
                    if not want_regfunc(regfunc.__name__):
                        continue
                    should_be_public = determine_whether_it_should_be_public(**locals())
                    (public if should_be_public else private).add(regfunc)
    return public, private

REGFUNCS_PUBLIC, REGFUNCS_PRIVATE = create_regfuncs()
REGFUNCS = REGFUNCS_PUBLIC | REGFUNCS_PRIVATE
_REGFUNCS_BY_NAME = {regfunc.__name__: regfunc for regfunc in REGFUNCS}

VARYFUNCS = (
    base,
    file_on,
    wiki_on,
) + tuple(REGFUNCS)


class TestVaryFuncs(DbIsolationMixin, OsfTestCase):

    # base

    def test_base_specifies_project_for_project(self):
        assert_equal(base(public_project())[1], 'project')

    def test_base_specifies_component_for_component(self):
        assert_equal(base(public_component_of_a_public_project())[1], 'component')


    # fo - file_on

    def test_fo_makes_a_file_on_a_node(self):
        file_on(factories.ProjectFactory())
        assert_equal(File.find_one(Q('is_file', 'eq', True)).name, 'Blim Blammity')


    # wo - wiki_on

    def test_wo_makes_a_wiki_on_a_node(self):
        project = factories.ProjectFactory()
        wiki_on(project)
        page = NodeWikiPage.load(project.wiki_pages_current['blim blammity'])
        assert_equal(page.page_name, 'Blim Blammity')
        assert_equal(page.content, 'Blim, blammity.')


    # regfuncs

    def Check(self, name):
        regfunc = _REGFUNCS_BY_NAME[name + '_registration_of_a']
        regfunc(factories.ProjectFactory(title='Flim Flammity'))
        reg = Node.find_one(Q('is_registration', 'eq', True))

        def check(retraction_state, embargo_state, approval_state, job_done):
            if retraction_state is None:
                ok_(reg.retraction is None)
            else:
                ok_(reg.retraction is not None)
                assert_equal(reg.retraction.state, retraction_state)

            if embargo_state is None:
                ok_(reg.embargo is None)
            else:
                ok_(reg.embargo is not None)
                assert_equal(reg.embargo.state, embargo_state)

            if approval_state is None:
                ok_(reg.registration_approval is None)
            else:
                ok_(reg.registration_approval is not None)
                assert_equal(reg.registration_approval.state, approval_state)

            if job_done:
                ok_(reg.archive_job.done)
            else:
                ok_(not reg.archive_job.done)

        return check

    def test_number_of_regfuncs(self):
        assert_equal(len(REGFUNCS), 32)

    def test_number_of_regfunc_tests(self):
        is_regfunc_test = lambda n: n.startswith('test_regfunc_')
        regfunc_tests = filter(is_regfunc_test, self.__class__.__dict__.keys())
        assert_equal(len(regfunc_tests), len(REGFUNCS))

    # no retraction
    def test_regfunc_uac(self):
        check = self.Check('unembargoed_approved_complete')
        check(None, None, 'approved', True)

    def test_regfunc_uai(self):
        check = self.Check('unembargoed_approved_incomplete')
        check(None, None, 'approved', False)

    def test_regfunc_uuc(self):
        check = self.Check('unembargoed_unapproved_complete')
        check(None, None, 'unapproved', True)

    def test_regfunc_uui(self):
        check = self.Check('unembargoed_unapproved_incomplete')
        check(None, None, 'unapproved', False)

    def test_regfunc_eac(self):
        check = self.Check('embargoed_approved_complete')
        check(None, 'approved', None, True)

    def test_regfunc_eai(self):
        check = self.Check('embargoed_approved_incomplete')
        check(None, 'approved', None, False)

    def test_regfunc_euc(self):
        check = self.Check('embargoed_unapproved_complete')
        check(None, 'unapproved', None, True)

    def test_regfunc_eui(self):
        check = self.Check('embargoed_unapproved_incomplete')
        check(None, 'unapproved', None, False)

    def test_regfunc_feac(self):
        check = self.Check('formerly_embargoed_approved_complete')
        check(None, 'completed', None, True)

    def test_regfunc_feai(self):
        check = self.Check('formerly_embargoed_approved_incomplete')
        check(None, 'completed', None, False)

    def test_regfunc_feuc(self):
        check = self.Check('formerly_embargoed_unapproved_complete')
        check(None, 'unapproved', None, True)

    def test_regfunc_feui(self):
        check = self.Check('formerly_embargoed_unapproved_incomplete')
        check(None, 'unapproved', None, False)

    # unapproved retraction
    def test_regfunc_uroauac(self):
        check = self.Check('unapproved_retraction_of_an_unembargoed_approved_complete')
        check('unapproved', None, 'approved', True)

    def test_regfunc_uroauai(self):
        check = self.Check('unapproved_retraction_of_an_unembargoed_approved_incomplete')
        check('unapproved', None, 'approved', False)

    def test_regfunc_uroaeac(self):
        check = self.Check('unapproved_retraction_of_an_embargoed_approved_complete')
        check('unapproved', 'approved', None, True)

    def test_regfunc_uroaeai(self):
        check = self.Check('unapproved_retraction_of_an_embargoed_approved_incomplete')
        check('unapproved', 'approved', None, False)

    def test_regfunc_uroaeuc(self):
        check = self.Check('unapproved_retraction_of_an_embargoed_unapproved_complete')
        check('unapproved', 'unapproved', None, True)

    def test_regfunc_uroaeui(self):
        check = self.Check('unapproved_retraction_of_an_embargoed_unapproved_incomplete')
        check('unapproved', 'unapproved', None, False)

    def test_regfunc_uroafeac(self):
        check = self.Check('unapproved_retraction_of_a_formerly_embargoed_approved_complete')
        check('unapproved', 'completed', None, True)

    def test_regfunc_uroafeai(self):
        check = self.Check('unapproved_retraction_of_a_formerly_embargoed_approved_incomplete')
        check('unapproved', 'completed', None, False)

    def test_regfunc_uroafeuc(self):
        check = self.Check('unapproved_retraction_of_a_formerly_embargoed_unapproved_complete')
        check('unapproved', 'unapproved', None, True)

    def test_regfunc_uroafeui(self):
        check = self.Check('unapproved_retraction_of_a_formerly_embargoed_unapproved_incomplete')
        check('unapproved', 'unapproved', None, False)

    # approved retraction
    def test_regfunc_aroauac(self):
        check = self.Check('approved_retraction_of_an_unembargoed_approved_complete')
        check('approved', None, 'approved', True)

    def test_regfunc_aroauai(self):
        check = self.Check('approved_retraction_of_an_unembargoed_approved_incomplete')
        check('approved', None, 'approved', False)

    def test_regfunc_aroaeac(self):
        check = self.Check('approved_retraction_of_an_embargoed_approved_complete')
        check('approved', 'rejected', None, True)

    def test_regfunc_aroaeai(self):
        check = self.Check('approved_retraction_of_an_embargoed_approved_incomplete')
        check('approved', 'rejected', None, False)

    def test_regfunc_aroaeuc(self):
        check = self.Check('approved_retraction_of_an_embargoed_unapproved_complete')
        check('approved', 'rejected', None, True)

    def test_regfunc_aroaeui(self):
        check = self.Check('approved_retraction_of_an_embargoed_unapproved_incomplete')
        check('approved', 'rejected', None, False)

    def test_regfunc_aroafeac(self):
        check = self.Check('approved_retraction_of_a_formerly_embargoed_approved_complete')
        check('approved', 'rejected', None, True)

    def test_regfunc_aroafeai(self):
        check = self.Check('approved_retraction_of_a_formerly_embargoed_approved_incomplete')
        check('approved', 'rejected', None, False)

    def test_regfunc_aroafeuc(self):
        check = self.Check('approved_retraction_of_a_formerly_embargoed_unapproved_complete')
        check('approved', 'rejected', None, True)

    def test_regfunc_aroafeui(self):
        check = self.Check('approved_retraction_of_a_formerly_embargoed_unapproved_incomplete')
        check('approved', 'rejected', None, False)

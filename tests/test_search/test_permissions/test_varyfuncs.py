# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import re

from nose.tools import assert_equal, ok_

from modularodm import Q
from framework.auth import Auth
from tests import factories
from tests.base import DbIsolationMixin
from tests.test_search import OsfTestCase
from tests.test_search.test_permissions.test_nodefuncs import (
    public_project, public_component_of_public_project
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
    return '{}{}{}_{}_{}_registration_of'.format(
        retraction_part,
        '' if not retraction else 'an_' if embargo in (None, True) else 'a_',
        'embargoed' if embargo else 'unembargoed' if embargo is None else 'previously_embargoed',
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
    for embargo in (None, True):   # never embargoed, presently embargoed, XXX previously embargoed
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

locals_dict = locals()
for regfunc in REGFUNCS:
    locals_dict[regfunc.__name__] = regfunc

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
        assert_equal(base(public_component_of_public_project())[1], 'component')


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

    def Reg(self, func):
        func(factories.ProjectFactory(title='Flim Flammity'))
        return Node.find_one(Q('is_registration', 'eq', True))

    def test_number_of_regfuncs(self):
        assert_equal(len(REGFUNCS), 20)

    def test_number_of_regfunc_tests(self):
        is_regfunc_test = lambda n: re.match('test_.*makes_an_.*_registration_of_a_node', n)
        regfunc_tests = filter(is_regfunc_test, self.__class__.__dict__.keys())
        assert_equal(len(regfunc_tests), len(REGFUNCS))

    # no retraction
    def test_uacro_makes_an_unembargoed_approved_complete_registration_of_a_node(self):
        reg = self.Reg(unembargoed_approved_complete_registration_of)
        ok_(reg.retraction is None)
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'approved')
        ok_(reg.archive_job.done)

    def test_uairo_makes_an_unembargoed_approved_incomplete_registration_of_a_node(self):
        reg = self.Reg(unembargoed_approved_incomplete_registration_of)
        ok_(reg.retraction is None)
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'approved')
        ok_(not reg.archive_job.done)

    def test_uucro_makes_an_unembargoed_unapproved_complete_registration_of_a_node(self):
        reg = self.Reg(unembargoed_unapproved_complete_registration_of)
        ok_(reg.retraction is None)
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'unapproved')
        ok_(reg.archive_job.done)

    def test_uuiro_makes_an_unembargoed_unapproved_incomplete_registration_of_a_node(self):
        reg = self.Reg(unembargoed_unapproved_incomplete_registration_of)
        ok_(reg.retraction is None)
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'unapproved')
        ok_(not reg.archive_job.done)

    def test_eacro_makes_an_embargoed_approved_complete_registration_of_a_node(self):
        reg = self.Reg(embargoed_approved_complete_registration_of)
        ok_(reg.retraction is None)
        assert_equal(reg.embargo.state, 'approved')
        ok_(reg.archive_job.done)

    def test_eairo_makes_an_embargoed_approved_incomplete_registration_of_a_node(self):
        reg = self.Reg(embargoed_approved_incomplete_registration_of)
        ok_(reg.retraction is None)
        assert_equal(reg.embargo.state, 'approved')
        ok_(not reg.archive_job.done)

    def test_eucro_makes_an_embargoed_unapproved_complete_registration_of_a_node(self):
        reg = self.Reg(embargoed_unapproved_complete_registration_of)
        ok_(reg.retraction is None)
        assert_equal(reg.embargo.state, 'unapproved')
        ok_(reg.archive_job.done)

    def test_euiro_makes_an_embargoed_unapproved_incomplete_registration_of_a_node(self):
        reg = self.Reg(embargoed_unapproved_incomplete_registration_of)
        ok_(reg.retraction is None)
        assert_equal(reg.embargo.state, 'unapproved')
        ok_(not reg.archive_job.done)

    # unapproved retraction
    def test_urouacro_makes_an_unapproved_retraction_of_an_unembargoed_approved_complete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_unembargoed_approved_complete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'approved')
        ok_(reg.archive_job.done)

    def test_urouairo_makes_an_unapproved_retraction_of_an_unembargoed_approved_incomplete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_unembargoed_approved_incomplete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'approved')
        ok_(not reg.archive_job.done)

    def test_uroeacro_makes_an_unapproved_retraction_of_an_embargoed_approved_complete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_embargoed_approved_complete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        assert_equal(reg.embargo.state, 'approved')
        ok_(reg.archive_job.done)

    def test_uroeairo_makes_an_unapproved_retraction_of_an_embargoed_approved_incomplete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_embargoed_approved_incomplete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        assert_equal(reg.embargo.state, 'approved')
        ok_(not reg.archive_job.done)

    def test_uroeucro_makes_an_unapproved_retraction_of_an_embargoed_unapproved_complete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_embargoed_unapproved_complete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        assert_equal(reg.embargo.state, 'unapproved')
        ok_(reg.archive_job.done)

    def test_uroeuiro_makes_an_unapproved_retraction_of_an_embargoed_unapproved_incomplete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_embargoed_unapproved_incomplete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        assert_equal(reg.embargo.state, 'unapproved')
        ok_(not reg.archive_job.done)

    # approved retraction
    def test_arouacro_makes_an_approved_retraction_of_an_unembargoed_approved_complete_registration_of_a_node(self):
        reg = self.Reg(approved_retraction_of_an_unembargoed_approved_complete_registration_of)
        assert_equal(reg.retraction.state, 'approved')
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'approved')
        ok_(reg.archive_job.done)

    def test_arouairo_makes_an_approved_retraction_of_an_unembargoed_approved_incomplete_registration_of_a_node(self):
        reg = self.Reg(approved_retraction_of_an_unembargoed_approved_incomplete_registration_of)
        assert_equal(reg.retraction.state, 'approved')
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'approved')
        ok_(not reg.archive_job.done)

    def test_aroeacro_makes_an_approved_retraction_of_an_embargoed_approved_complete_registration_of_a_node(self):
        reg = self.Reg(approved_retraction_of_an_embargoed_approved_complete_registration_of)
        assert_equal(reg.retraction.state, 'approved')
        assert_equal(reg.embargo.state, 'rejected')
        ok_(reg.archive_job.done)

    def test_aroeairo_makes_an_approved_retraction_of_an_embargoed_approved_incomplete_registration_of_a_node(self):
        reg = self.Reg(approved_retraction_of_an_embargoed_approved_incomplete_registration_of)
        assert_equal(reg.retraction.state, 'approved')
        assert_equal(reg.embargo.state, 'rejected')
        ok_(not reg.archive_job.done)

    def test_aroeucro_makes_an_approved_retraction_of_an_embargoed_unapproved_complete_registration_of_a_node(self):
        reg = self.Reg(approved_retraction_of_an_embargoed_unapproved_complete_registration_of)
        assert_equal(reg.retraction.state, 'approved')
        assert_equal(reg.embargo.state, 'rejected')
        ok_(reg.archive_job.done)

    def test_aroeuiro_makes_an_approved_retraction_of_an_embargoed_unapproved_incomplete_registration_of_a_node(self):
        reg = self.Reg(approved_retraction_of_an_embargoed_unapproved_incomplete_registration_of)
        assert_equal(reg.retraction.state, 'approved')
        assert_equal(reg.embargo.state, 'rejected')
        ok_(not reg.archive_job.done)

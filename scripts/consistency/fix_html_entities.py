"""Removes HTML escape sequences from objects in the database.

Previously, sanitizing user input occurred in various places in the codebase:
on input, before being saved to the DB, before being passed to a template, and
in templates.

We have now standardized on storing all user input as-is in the database, and
escaping it when it is displayed back to the user.

This script unescapes data that was existent in the database when this change
was made.

This script must be run from the OSF root directory for the imports to work.
::

    $ python -m scripts.consistency.fix_html_entities dry
    $ python -m scripts.consistency.fix_html_entities
"""
import re
import sys
import HTMLParser

from modularodm import Q
from nose.tools import *  # noqa

from framework.auth import Auth

from website.app import init_app
from website.models import Node, NodeLog

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory

parser = HTMLParser.HTMLParser()

CONTAINS_ENCODED_CHARACTERS = re.compile("&[^ ]*?;")


def main():
    # Set up storage backends
    init_app(routes=False)

    dry_run = 'dry' in sys.argv

    # Fields of the Node object
    for field in ('title', 'description'):
        print("Nodes ({})\n=====".format(field))
        nodes = find_encoded_objects(Node, field)
        for node in nodes:
            print("{}".format(node._id))
            if not dry_run:
                fix_encoded_object(node, field)
                node.save()


def find_encoded_objects(model, field):
    return model.find(Q(field, 'eq', CONTAINS_ENCODED_CHARACTERS))


def fix_encoded_object(obj, field):
    setattr(obj, field, unescape(getattr(obj, field)))
    return obj


def unescape(val):
    if isinstance(val, dict):
        return {
            k: v if v is None else parser.unescape(v)
            for k, v in val.iteritems()
        }
    return parser.unescape(val)


class TestMigrateEncodedLogs(OsfTestCase):
    _escaped = {
        'title_new': 'A &lt;b&gt;bold&lt;/b&gt; new title',
        'title_original': 'A &lt;b&gt;bold&lt;/b&gt; original title',
    }

    _raw = {
        'title_new': 'A <b>bold</b> new title',
        'title_original': 'A <b>bold</b> original title',
    }

    def setUp(self):
        super(TestMigrateEncodedLogs, self).setUp()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory()

        self.logs = {
            'correct': self.__add_log(
                title_new=self._raw['title_new'],
                title_original=self._raw['title_original'],
            ),
            'escaped': self.__add_log(
                title_new=self._escaped['title_new'],
                title_original=self._escaped['title_original'],
            )
        }

    def __add_log(self, title_new, title_original):
        return self.project.add_log(
            action=NodeLog.EDITED_TITLE,
            params={
                'project': None,
                'node': self.project._id,
                'title_new': title_new,
                'title_original': title_original,
            },
            auth=Auth(user=self.user),
            save=False,
        )

    def test_fix_unescaped(self):
        log = self.logs['correct']
        original_params = log.params.copy()

        log.params = unescape(log.params)

        assert_equal(original_params, log.params)

    def test_fix_escaped(self):
        log = self.logs['escaped']
        original_params = log.params.copy()
        corrected_params = log.params.copy()
        corrected_params.update(self._raw)

        log.params = unescape(log.params)

        assert_not_equal(original_params, log.params)
        assert_equal(corrected_params, log.params)




class TestMigrateEncodedNodes(OsfTestCase):

    _escaped = {
        'title': 'This &amp; That',
        'description': 'A &lt;b&gt;bold&lt;/b&gt; description',
    }

    _raw = {
        'title': 'This & That',
        'description': 'A <b>bold</b> description',
    }

    def setUp(self):
        super(TestMigrateEncodedNodes, self).setUp()
        self.raw_project = ProjectFactory(**self._raw)
        self.escaped_project = ProjectFactory(**self._escaped)

    def test_find_nodes(self):
        results = find_encoded_objects(Node, 'title')
        assert_equal(results.count(), 1)
        assert_equal(results[0], self.escaped_project)

    def test_fix_raw_node_title(self):
        node = fix_encoded_object(self.raw_project, 'title')
        node.save()
        assert_equal(node.title, self._raw['title'])

    def test_fix_escaped_node_title(self):
        node = fix_encoded_object(self.escaped_project, 'title')
        assert_equal(node.title, self._raw['title'])


if __name__ == '__main__':
    main()
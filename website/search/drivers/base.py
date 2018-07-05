import abc
import logging

import deprecation

from osf import models
from website import settings


logger = logging.getLogger(__name__)


class SearchDriver(object):

    __metaclass__ = abc.ABCMeta

    # TODO Remove me
    DOC_TYPE_TO_MODEL = {
        'component': models.AbstractNode,
        'file': models.BaseFileNode,
        'institution': models.Institution,
        'preprint': models.AbstractNode,
        'project': models.AbstractNode,
        'registration': models.AbstractNode,
        'user': models.OSFUser,
    }
    # and me
    ALIASES = {
        'project': 'Projects',
        'component': 'Components',
        'registration': 'Registrations',
        'user': 'Users',
        'total': 'All OSF Results',
        'file': 'Files',
        'institution': 'Institutions',
        'preprint': 'Preprints',
    }

    INDEXABLE_TYPES = (
        'collection-submissions',
        # 'collections',
        'components',
        'files',
        'institutions',
        'preprints',
        'projects',
        'registrations',
        'users',
    )

    ### Migration API ###

    @abc.abstractmethod
    def setup(self, types=None):
        raise NotImplementedError()

    def _before_migrate(self, types):
        pass

    def migrate(self, types=None):
        types = types or self.INDEXABLE_TYPES

        for type_ in types:
            if type_ not in self.INDEXABLE_TYPES:
                raise Exception('Unable to index unknown type "{}"'.format(type_))

        self.setup(types)
        self._before_migrate(types)

        for type_ in types:
            logger.info('Indexing all %s', type_)
            count = getattr(self, 'index_{}'.format(type_.replace('-', '_')))()
            logger.info('Indexed %d %s', count, type_)

        self._after_migrate(types)

    @abc.abstractmethod
    def teardown(self, types=None):
        raise NotImplementedError()

    def _after_migrate(self, types):
        pass

    ### /Migration API ###

    ### NEW API ###

    # NOTE: index_type methods are 

    @abc.abstractproperty
    def index_files(self, **query):
        raise NotImplementedError()

    @abc.abstractproperty
    def index_users(self, **query):
        raise NotImplementedError()

    @abc.abstractproperty
    def index_institutions(self, **query):
        raise NotImplementedError()

    @abc.abstractproperty
    def index_registrations(self, **query):
        raise NotImplementedError()

    @abc.abstractproperty
    def index_projects(self, **query):
        raise NotImplementedError()

    @abc.abstractproperty
    def index_components(self, **query):
        raise NotImplementedError()

    @abc.abstractproperty
    def index_preprints(self, **query):
        raise NotImplementedError()

    @abc.abstractproperty
    def index_collection_submissions(self, **query):
        raise NotImplementedError()

    @abc.abstractproperty
    def remove(self, model_instance):
        raise NotImplementedError()

    def index_nodes(self, **query):
        # Not the best thing in the entire world but it makes life a bit easier for everyone
        # The methods will filter out anything not applicable to them so this is in fact safe
        return sum([
            self.index_components(**query),
            self.index_preprints(**query),
            self.index_projects(**query),
            self.index_registrations(**query),
        ])

    # / NEW API

    # These need to be rewritten at somepoint
    @abc.abstractmethod
    def search(self, query, index=None, doc_type=None, raw=None, refresh=False):
        raise NotImplementedError()

    @abc.abstractmethod
    def search_contributor(query, page=0, size=10, exclude=None, current_user=None):
        raise NotImplementedError()

    # Deprecated API :(
    @deprecation.deprecated(
        removed_in='0.155.0',
        deprecated_in='0.145.0',
        current_version=settings.VERSION,
        details='Use .index_nodes(pk=node_id) or .index_<node_type>(pk=node_id), followed by .index_files(node_id=node.id) on CelerySearchDelegator instead',
    )
    def update_node_async(self, node_id, index=None, bulk=False):
        logger.warning('update_node_async is no longer async by default. Use CelerySearchDelegator for async search operations')
        # TODO can this be trusted to be a pk??
        return self.update_node(models.AbstractNode.load(node_id).id)

    @deprecation.deprecated(
        removed_in='0.155.0',
        deprecated_in='0.145.0',
        current_version=settings.VERSION,
        details='Use .index_nodes(pk=node.id) or .index_<node_type> if it is known, followed by .index_files(node_id=node.id) instead',
    )
    def update_node(self, node, index=None, bulk=False, async=False):
        if node.is_registration:
            ret = self.index_registrations(pk=node.id)
        elif node.is_preprint:
            ret = self.index_preprints(pk=node.id)
        elif node.parent_node:
            ret = self.index_components(pk=node.id)
        else:
            ret = self.index_projects(pk=node.id)
        self.index_files(node_id=node.id)
        return ret

    @deprecation.deprecated(
        removed_in='0.155.0',
        deprecated_in='0.145.0',
        current_version=settings.VERSION,
        details=(
            'Use .index_registrations, .index_components, .index_projects, '
            'or .index_preprints with (pk__in=node_ids) instead'
        ),
    )
    def bulk_update_nodes(self, serialize, nodes, index=None):
        types = {
            'registrations': [],
            'projects': [],
            'components': [],
            'preprints': [],
        }
        for node in nodes:
            if node.is_registration:
                types['registrations'].append(node.id)
            elif node.is_preprint:
                types['preprints'].append(node.id)
            elif node.parent_node:
                types['components'].append(node.id)
            else:
                types['projects'].append(node.id)

        ret = 0
        for type_, nids in types.items():
            if not nids:
                continue
            ret += getattr(self, 'index_{}'.format(type_))(pk__in=nids)

        self.index_files(node_id__in=[n.id for n in nodes])
        return ret

    @deprecation.deprecated(
        removed_in='0.155.0',
        deprecated_in='0.145.0',
        current_version=settings.VERSION,
        details='Use .index_users(pk=user.id) or .remove(user) on CelerySearchDelegator instead',
    )
    def update_user_async(self, user_id, index=None):
        logger.warning('update_user_async is no longer async by default. Use CelerySearchDelegator for async search operations')
        return self.index_users(pk=user_id)

    @deprecation.deprecated(
        removed_in='0.155.0',
        deprecated_in='0.145.0',
        current_version=settings.VERSION,
        details='Use .index_users(pk=user.id) or .remove(user)',
    )
    def update_user(self, user, index=None):
        return self.index_users(pk=user.id)

    @deprecation.deprecated(
        removed_in='0.155.0',
        deprecated_in='0.145.0',
        current_version=settings.VERSION,
        details='Use .index_nodes(contributor__user_id=user_id) on CelerySearchDelegator instead',
    )
    def update_contributors_async(self, user_id):
        logger.warning('update_contributors_async is no longer async by default. Use CelerySearchDelegator for async search operations')
        return self.index_files(node__contributor__user_id=user_id)
        return self.index_nodes(contributor__user_id=user_id)

    @deprecation.deprecated(
        removed_in='0.155.0',
        deprecated_in='0.145.0',
        current_version=settings.VERSION,
        details='Use .index_files(pk=file_node.id) instead',
    )
    def update_file(self, file_node, index=None, delete=False):
        return self.index_files(pk=file_node.id)

    @deprecation.deprecated(
        removed_in='0.155.0',
        deprecated_in='0.145.0',
        current_version=settings.VERSION,
        details='Use .index_institutions or .remove(institution) instead',
    )
    def update_institution(self, institution):
        return self.index_institutions(pk=institution.id)

    @deprecation.deprecated(
        removed_in='0.155.0',
        deprecated_in='0.145.0',
        current_version=settings.VERSION,
        details='Use .remove(node)',
    )
    def delete_node(self, node, index=None):
        return self.index_node(pk=node.id)

    # / Deprecated API

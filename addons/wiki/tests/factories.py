import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, NodeFactory

from addons.wiki.models import NodeWikiPage

class NodeWikiFactory(DjangoModelFactory):
    class Meta:
        model = NodeWikiPage

    page_name = 'home'
    content = 'Some content'
    version = 1
    user = factory.SubFactory(UserFactory)
    node = factory.SubFactory(NodeFactory)

    @factory.post_generation
    def set_node_keys(self, create, extracted):
        self.node.wiki_pages_current[self.page_name] = self._id
        if self.node.wiki_pages_versions.get(self.page_name, None):
            self.node.wiki_pages_versions[self.page_name].append(self._id)
        else:
            self.node.wiki_pages_versions[self.page_name] = [self._id]
        self.node.save()

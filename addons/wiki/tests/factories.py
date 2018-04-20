import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, NodeFactory

from addons.wiki.models import WikiPage, WikiVersion

class WikiFactory(DjangoModelFactory):
    class Meta:
        model = WikiPage

    page_name = 'home'
    user = factory.SubFactory(UserFactory)
    node = factory.SubFactory(NodeFactory)

class WikiVersionFactory(DjangoModelFactory):
    class Meta:
        model = WikiVersion

    user = factory.SubFactory(UserFactory)
    wiki_page = factory.SubFactory(WikiFactory)
    content = 'First draft of wiki'
    identifier = 1

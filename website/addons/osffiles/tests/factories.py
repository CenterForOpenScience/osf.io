
from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, NodeFactory

from ..model import OsfGuidFile


class OsfGuidFileFactory(ModularOdmFactory):
    FACTORY_FOR = OsfGuidFile

    name = Sequence(lambda n: 'myfile{0}.rst'.format(n))
    node = SubFactory(NodeFactory)

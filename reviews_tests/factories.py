import factory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
)

from reviews import models
from reviews import workflow


class ReviewLogFactory(DjangoModelFactory):
    class Meta:
        model = models.ReviewLog

    action = FuzzyChoice(choices=workflow.Actions.values())
    comment = factory.Faker('text')
    from_state = FuzzyChoice(choices=workflow.States.values())
    to_state = FuzzyChoice(choices=workflow.States.values())

    reviewable = factory.SubFactory(PreprintFactory)
    creator = factory.SubFactory(AuthUserFactory)

    is_deleted = False

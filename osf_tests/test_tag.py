import pytest

from osf.models import Tag
from osf.exceptions import ValidationError

@pytest.mark.django_db
class TestTag:

    def test_has_an_integer_pk(self):
        tag = Tag(name='FooBar')
        tag.save()
        assert type(tag.pk) is int

    def test_uniqueness_on_name_and_system(self):
        tag = Tag(name='FooBar', system=False)
        tag.save()

        tag2 = Tag(name='FooBar', system=False)
        with pytest.raises(ValidationError):
            tag2.save()

        tag3 = Tag(name='FooBar', system=True)
        try:
            tag3.save()
        except Exception:
            pytest.fail('Saving system tag with non-unique name should not error.')

    def test_load_loads_by_name(self):
        tag_name = 'NeONDreams'
        tag = Tag(name=tag_name)
        tag.save()

        assert Tag.load(tag_name).pk == tag.pk

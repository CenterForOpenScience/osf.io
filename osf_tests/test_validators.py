import pytest
from osf.exceptions import ValidationValueError

from osf.models import validators

# Ported from tests/framework/test_mongo.py

def test_string_required_passes_with_string():
    assert validators.string_required('Hi!') is True

def test_string_required_fails_when_empty():
    with pytest.raises(ValidationValueError):
        validators.string_required(None)
    with pytest.raises(ValidationValueError):
        validators.string_required('')

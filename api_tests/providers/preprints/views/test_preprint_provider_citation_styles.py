from django.urls import reverse
from osf.models import CitationStyle
from osf_tests.factories import PreprintProviderFactory
from osf.admin.preprint_providers.forms import PreprintProviderForm


def test_retrieval_of_citation_styles_for_specific_preprint_provider(self):
    # Setup
    preprint_provider = PreprintProviderFactory()
    # Define the expected citation styles
    # TODO: Must be a better way to do this
    expected_citation_styles = ['apa', 'chicago-author-date', 'modern-language-association']

    # Action
    response = self.client.get(reverse('preprintprovidercitationstyles-view', args=[preprint_provider.id]))

    # Assert
    assert response.status_code == 200
    assert response.data == expected_citation_styles


def test_retrieval_of_no_preferred_citation_styles(self):
    # Setup
    preprint_provider = PreprintProviderFactory()  # Assuming no preferred citation styles

    # Action
    response = self.client.get(reverse('preprintprovidercitationstyles-view', args=[preprint_provider.id]))

    # Assert
    assert response.status_code == 200
    assert response.data == []  # Expecting an empty list if no preferred styles


def test_admin_form_with_valid_citation_styles(self):
    # Setup
    citation_styles = CitationStyle.objects.all()[:3]  # Assuming you want to test with three styles
    data = {
        'citation_styles': citation_styles,
        # TODO: Other fields required for the form
    }

    # Action
    form = PreprintProviderForm(data)

    # Assert
    assert form.is_valid()
    assert form.cleaned_data['citation_styles'] == list(citation_styles)


def test_admin_form_with_invalid_citation_styles(self):
    # Setup
    citation_styles = ['invalid_style']  # Invalid citation styles
    data = {
        'citation_styles': citation_styles,
        # TODO: Other fields required for the form
    }

    # Action
    form = PreprintProviderForm(data)

    # Assert
    assert not form.is_valid()
    assert 'citation_styles' in form.errors

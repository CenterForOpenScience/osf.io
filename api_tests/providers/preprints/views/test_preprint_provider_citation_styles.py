from django.test import TestCase
from django.urls import reverse
from admin.preprint_providers.forms import PreprintProviderForm
from osf.models import CitationStyle
from osf_tests.factories import PreprintProviderFactory

class TestPreprintProviderCitationStyles(TestCase):
    def test_retrieval_of_citation_styles_for_specific_preprint_provider(self):
        preprint_provider = PreprintProviderFactory()
        expected_citation_styles = ['apa', 'chicago-author-date', 'modern-language-association']
        response = self.client.get(reverse('preprint-provider-citation-styles', args=[preprint_provider.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_citation_styles)

    def test_retrieval_of_no_preferred_citation_styles(self):
        preprint_provider = PreprintProviderFactory()  # Assuming no preferred citation styles
        response = self.client.get(reverse('preprint-provider-citation-styles', args=[preprint_provider.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])  # Expecting an empty list if no preferred styles

    def test_admin_form_with_valid_citation_styles(self):
        citation_styles = CitationStyle.objects.all()[:3]  # Assuming you want to test with three styles
        data = {
            'citation_styles': citation_styles,
        }
        form = PreprintProviderForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['citation_styles'], list(citation_styles))

    def test_admin_form_with_invalid_citation_styles(self):
        citation_styles = ['invalid_style']  # Invalid citation styles
        data = {
            'citation_styles': citation_styles,
        }
        form = PreprintProviderForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('citation_styles', form.errors)


from django.db.models import Q
from guardian.shortcuts import get_objects_for_user
from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotAuthenticated

from api.base import permissions as base_permissions
from api.base.exceptions import InvalidFilterValue, InvalidFilterOperator, Conflict
from api.base.filters import PreprintFilterMixin, ListFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.pagination import MaxSizePagination
from api.base.utils import get_object_or_error, get_user_auth, is_truthy
from api.licenses.views import LicenseList
from api.taxonomies.serializers import TaxonomySerializer
from api.taxonomies.utils import optimize_subject_query
from api.preprint_providers.serializers import PreprintProviderSerializer
from api.preprint_providers.permissions import CanSetUpProvider, PERMISSIONS
from api.preprints.serializers import PreprintSerializer
from api.preprints.permissions import PreprintPublishedOrAdmin
from framework.auth.oauth_scopes import CoreScopes
from osf.models import AbstractNode, Subject, PreprintProvider

class PreprintProviderList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    """
    Paginated list of verified PreprintProviders available. *Read-only*

    Assume undocumented fields are unstable.

    ##PreprintProvider Attributes

    OSF Preprint Providers have the "preprint_providers" `type`.

        name                       type                description
        =============================================================================================================
        name                       string              name of the preprint provider
        logo_path                  string              a path to the preprint provider's static logo
        banner_path                string              a path to the preprint provider's banner
        description                string              description of the preprint provider
        advisory_board             string              HTML for the advisory board/steering committee section
        email_contact              string              the contact email for the preprint provider
        email_support              string              the support email for the preprint provider
        social_facebook            string              the preprint provider's Facebook account
        social_instagram           string              the preprint provider's Instagram account
        social_twitter             string              the preprint provider's Twitter account
        domain                     string              the domain name of the preprint provider
        domain_redirect_enabled    boolean             whether or not redirects are enabled for the provider's domain
        example                    string              an example guid for a preprint created for the preprint provider
        reviews_workflow           string              the workflow used for reviewing/moderating preprints, if any
        reviews_comments_private   boolean             whether comments made by moderators are visible to authors
        reviews_comments_anonymous boolean             if comments are not private, whether the name of the moderator is visible to authors

    ##Relationships

    ###Preprints
    Link to the list of preprints from this given preprint provider.

    ##Links

        self: the canonical api endpoint of this preprint provider
        preprints: link to the provider's preprints
        external_url: link to the preprint provider's external URL (e.g. https://socarxiv.org)

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    model_class = PreprintProvider

    pagination_class = MaxSizePagination
    serializer_class = PreprintProviderSerializer
    view_category = 'preprint_providers'
    view_name = 'preprint_providers-list'

    ordering = ('name', )

    def get_default_queryset(self):
        return PreprintProvider.objects.all()

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()

    def build_query_from_field(self, field_name, operation):
        if field_name == 'permissions':
            if operation['op'] != 'eq':
                raise InvalidFilterOperator(value=operation['op'], valid_operators=['eq'])
            auth = get_user_auth(self.request)
            auth_user = getattr(auth, 'user', None)
            if not auth_user:
                raise NotAuthenticated()
            value = operation['value'].lstrip('[').rstrip(']')
            permissions = [v.strip() for v in value.split(',')]
            if any(p not in PERMISSIONS for p in permissions):
                valid_permissions = ', '.join(PERMISSIONS.keys())
                raise InvalidFilterValue('Invalid permission! Valid values are: {}'.format(valid_permissions))
            return Q(id__in=get_objects_for_user(auth_user, permissions, PreprintProvider, any_perm=True))

        return super(PreprintProviderList, self).build_query_from_field(field_name, operation)


class PreprintProviderDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView):
    """ Details about a given preprint provider. *Writeable*

    Assume undocumented fields are unstable.

    ##PreprintProvider Attributes

    OSF Preprint Providers have the "preprint_providers" `type`.

        name                       type                description
        =============================================================================================================
        name                       string              name of the preprint provider
        logo_path                  string              a path to the preprint provider's static logo
        banner_path                string              a path to the preprint provider's banner
        description                string              description of the preprint provider
        advisory_board             string              HTML for the advisory board/steering committee section
        email_contact              string              the contact email for the preprint provider
        email_support              string              the support email for the preprint provider
        social_facebook            string              the preprint provider's Facebook account
        social_instagram           string              the preprint provider's Instagram account
        social_twitter             string              the preprint provider's Twitter account
        domain                     string              the domain name of the preprint provider
        domain_redirect_enabled    boolean             whether or not redirects are enabled for the provider's domain
        example                    string              an example guid for a preprint created for the preprint provider
        reviews_workflow           string              the workflow used for reviewing/moderating preprints, if any
        reviews_comments_private   boolean             whether comments made by moderators are visible to authors
        reviews_comments_anonymous boolean             if comments are not private, whether the name of the moderator is visible to authors

    ##Relationships

    ###Preprints
    Link to the list of preprints from this given preprint provider.

    ##Links

        self: the canonical api endpoint of this preprint provider
        preprints: link to the provider's preprints
        external_url: link to the preprint provider's external URL (e.g. https://socarxiv.org)

    ##Setting up Moderation

    Set up moderation for a provider by sending a patch request to the ID of the existing provider.

    Currently, the only parameters which may be set are `reviews_workflow`,
    `reviews_comments_private`, and `reviews_comments_anonymous`. These parameters may be set
    only once, after which they may be updated only by an OSF Admin.

    If `reviews_workflow` is already non-null, attempting to update the provider will return
    a `409` Conflict error. If you need to change your provider's moderation settings, contact
    [support@osf.io](mailto:support@osf.io) for help.

        Method:        PATCH
        URL:           /preprint_providers/{provider_id}/
        Query Params:  <none>
        Body (JSON):   {
                        "data": {
                            "id": provider_id,
                            "attributes": {
                                "reviews_workflow": {workflow},  # Valid workflows: "pre-moderation", "post-moderation"
                                "reviews_comments_private": {boolean},
                                "reviews_comments_anonymous": {boolean}
                            },
                        }
                    }
        Success:       200 OK + provider representation

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CanSetUpProvider,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.PROVIDERS_WRITE]
    model_class = PreprintProvider

    serializer_class = PreprintProviderSerializer
    view_category = 'preprint_providers'
    view_name = 'preprint_provider-detail'

    def get_object(self):
        provider = get_object_or_error(PreprintProvider, self.kwargs['provider_id'], self.request, display_name='PreprintProvider')
        self.check_object_permissions(self.request, provider)
        return provider

    def perform_update(self, serializer):
        if serializer.instance.is_reviewed:
            raise Conflict('Reviews settings may be set only once. Contact support@osf.io if you need to update them.')
        super(PreprintProviderDetail, self).perform_update(serializer)


class PreprintProviderPreprintList(JSONAPIBaseView, generics.ListAPIView, PreprintFilterMixin):
    """Preprints from a given preprint_provider. *Read Only*

    To update preprints with a given preprint_provider, see the `<node_id>/relationships/preprint_provider` endpoint

    ##Preprint Attributes

    OSF Preprint entities have the "preprints" `type`.

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the preprint was created
        date_modified                   iso8601 timestamp                   timestamp that the preprint was last modified
        date_published                  iso8601 timestamp                   timestamp when the preprint was published
        original_publication_date       iso8601 timestamp                   user-entered date of publication from external posting
        is_published                    boolean                             whether or not this preprint is published
        is_preprint_orphan              boolean                             whether or not this preprint is orphaned
        subjects                        array of tuples of dictionaries     ids of Subject in the BePress taxonomy. Dictionary, containing the subject text and subject ID
        doi                             string                              bare DOI for the manuscript, as entered by the user

    ##Relationships

    ###Node
    The node that this preprint was created for

    ###Primary File
    The file that is designated as the preprint's primary file, or the manuscript of the preprint.

    ###Provider
    Link to preprint_provider detail for this preprint

    ##Links
    - `self` -- Preprint detail page for the current preprint
    - `html` -- Project on the OSF corresponding to the current preprint
    - `doi` -- URL representation of the DOI entered by the user for the preprint manuscript

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PreprintPublishedOrAdmin,
    )

    ordering = ('-created')

    serializer_class = PreprintSerializer
    model_class = AbstractNode

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'preprint_providers'
    view_name = 'preprints-list'

    def get_default_queryset(self):
        auth = get_user_auth(self.request)
        auth_user = getattr(auth, 'user', None)
        provider = get_object_or_error(PreprintProvider, self.kwargs['provider_id'], self.request, display_name='PreprintProvider')

        # Permissions on the list objects are handled by the query
        return self.preprints_queryset(provider.preprint_services.all(), auth_user)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()

    # overrides APIView
    def get_renderer_context(self):
        context = super(PreprintProviderPreprintList, self).get_renderer_context()
        show_counts = is_truthy(self.request.query_params.get('meta[reviews_state_counts]', False))
        if show_counts:
            # TODO don't duplicate the above
            auth = get_user_auth(self.request)
            auth_user = getattr(auth, 'user', None)
            provider = get_object_or_error(PreprintProvider, self.kwargs['provider_id'], self.request, display_name='PreprintProvider')
            if auth_user and auth_user.has_perm('view_submissions', provider):
                context['meta'] = {
                    'reviews_state_counts': provider.get_reviewable_state_counts(),
                }
        return context


class PreprintProviderTaxonomies(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_category = 'preprint_providers'
    view_name = 'taxonomy-list'

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = TaxonomySerializer

    ordering = ('-id',)

    def is_valid_subject(self, allows_children, allowed_parents, sub):
        # TODO: Delet this when all PreprintProviders have a mapping
        if sub._id in allowed_parents:
            return True
        if sub.parent:
            if sub.parent._id in allows_children:
                return True
            if sub.parent.parent:
                if sub.parent.parent._id in allows_children:
                    return True
        return False

    def get_queryset(self):
        parent = self.request.query_params.get('filter[parents]', None) or self.request.query_params.get('filter[parent]', None)
        provider = get_object_or_error(PreprintProvider, self.kwargs['provider_id'], self.request, display_name='PreprintProvider')
        if parent:
            if parent == 'null':
                return provider.top_level_subjects
            if provider.subjects.exists():
                return optimize_subject_query(provider.subjects.filter(parent___id=parent))
            else:
                # TODO: Delet this when all PreprintProviders have a mapping
                #  Calculate this here to only have to do it once.
                allowed_parents = [id_ for sublist in provider.subjects_acceptable for id_ in sublist[0]]
                allows_children = [subs[0][-1] for subs in provider.subjects_acceptable if subs[1]]
                return [sub for sub in optimize_subject_query(Subject.objects.filter(parent___id=parent)) if provider.subjects_acceptable == [] or self.is_valid_subject(allows_children=allows_children, allowed_parents=allowed_parents, sub=sub)]
        return optimize_subject_query(provider.all_subjects)


class PreprintProviderHighlightedSubjectList(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_category = 'preprint_providers'
    view_name = 'highlighted-taxonomy-list'

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = TaxonomySerializer

    def get_queryset(self):
        provider = get_object_or_error(PreprintProvider, self.kwargs['provider_id'], self.request, display_name='PreprintProvider')
        return optimize_subject_query(Subject.objects.filter(id__in=[s.id for s in provider.highlighted_subjects]).order_by('text'))


class PreprintProviderLicenseList(LicenseList):
    ordering = ()  # TODO: should be ordered once the frontend for selecting default licenses no longer relies on order
    view_category = 'preprint_providers'

    def get_queryset(self):
        provider = get_object_or_error(PreprintProvider, self.kwargs['provider_id'], self.request, display_name='PreprintProvider')
        if not provider.licenses_acceptable.count():
            if not provider.default_license:
                return super(PreprintProviderLicenseList, self).get_queryset()
            return [provider.default_license] + [license for license in super(PreprintProviderLicenseList, self).get_queryset() if license != provider.default_license]
        if not provider.default_license:
            return provider.licenses_acceptable.get_queryset()
        return [provider.default_license] + [license for license in provider.licenses_acceptable.all() if license != provider.default_license]

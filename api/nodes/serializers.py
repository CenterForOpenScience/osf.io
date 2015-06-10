from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, LinksField, Link, WaterbutlerLink
from website.models import Node
from framework.auth.core import Auth
from website.project.model import MetaSchema
from modularodm import Q
from framework.forms.utils import process_payload
from rest_framework import serializers
import json
from api.base.utils import absolute_reverse
from api.base.utils import token_creator
from website.language import REGISTER_WARNING
from django.utils.translation import ugettext_lazy as _


class NodeSerializer(JSONAPISerializer):
    # TODO: If we have to redo this implementation in any of the other serializers, subclass ChoiceField and make it
    # handle blank choices properly. Currently DRF ChoiceFields ignore blank options, which is incorrect in this
    # instance
    category_choices = Node.CATEGORY_MAP.keys()
    category_choices_string = ', '.join(["'{}'".format(choice) for choice in category_choices])
    filterable_fields = frozenset(['title', 'description', 'public'])

    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(required=True)
    description = ser.CharField(required=False, allow_blank=True, allow_null=True)
    category = ser.ChoiceField(choices=category_choices, help_text="Choices: " + category_choices_string)
    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    tags = ser.SerializerMethodField(help_text='A dictionary that contains two lists of tags: '
                                               'user and system. Any tag that a user will define in the UI will be '
                                               'a user tag')

    links = LinksField({
        'html': 'get_absolute_url',
        'children': {
            'related': Link('nodes:node-children', kwargs={'pk': '<pk>'}),
            'count': 'get_node_count',
        },
        'contributors': {
            'related': Link('nodes:node-contributors', kwargs={'pk': '<pk>'}),
            'count': 'get_contrib_count',
        },
        'pointers': {
            'related': Link('nodes:node-pointers', kwargs={'pk': '<pk>'}),
            'count': 'get_pointers_count',
        },
        'registrations': {
            'related': Link('nodes:node-registrations', kwargs={'pk': '<pk>'}),
            'count': 'get_registration_count',
        },
        'files': {
            'related': Link('nodes:node-files', kwargs={'pk': '<pk>'})
        },
    })
    properties = ser.SerializerMethodField(help_text='A dictionary of read-only booleans: registration, collection,'
                                                     'and dashboard. Collections are special nodes used by the Project '
                                                     'Organizer to, as you would imagine, organize projects. '
                                                     'A dashboard is a collection node that serves as the root of '
                                                     'Project Organizer collections. Every user will always have '
                                                     'one Dashboard')
    # TODO: When we have 'admin' permissions, make this writable for admins
    public = ser.BooleanField(source='is_public', read_only=True,
                              help_text='Nodes that are made public will give read-only access '
                                                            'to everyone. Private nodes require explicit read '
                                                            'permission. Write and admin access are the same for '
                                                            'public and private nodes. Administrators on a parent '
                                                            'node have implicit read permissions for all child nodes',
                              )
    # TODO: finish me

    class Meta:
        type_ = 'nodes'

    def get_absolute_url(self, obj):
        return obj.absolute_url

    # TODO: See if we can get the count filters into the filter rather than the serializer.

    def get_user_auth(self, request):
        user = request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        return auth

    def get_node_count(self, obj):
        auth = self.get_user_auth(self.context['request'])
        nodes = [node for node in obj.nodes if node.can_view(auth) and node.primary]
        return len(nodes)

    def get_contrib_count(self, obj):
        return len(obj.contributors)

    def get_registration_count(self, obj):
        auth = self.get_user_auth(self.context['request'])
        registrations = [node for node in obj.node__registrations if node.can_view(auth)]
        return len(registrations)

    def get_pointers_count(self, obj):
        return len(obj.nodes_pointer)

    @staticmethod
    def get_properties(obj):
        ret = {
            'registration': obj.is_registration,
            'collection': obj.is_folder,
            'dashboard': obj.is_dashboard,
        }
        return ret

    @staticmethod
    def get_tags(obj):
        ret = {
            'system': [tag._id for tag in obj.system_tags],
            'user': [tag._id for tag in obj.tags],
        }
        return ret

    def create(self, validated_data):
        node = Node(**validated_data)
        node.save()
        return node

    def update(self, instance, validated_data):
        """Update instance with the validated data. Requires
        the request to be in the serializer context.
        """
        assert isinstance(instance, Node), 'instance must be a Node'
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class RegistrationWithTokenMixin(JSONAPISerializer):
    def validate(self, data):
        request = self.context['request']
        user = request.user
        view = self.context['view']
        node = view.get_node()
        given_token = view.kwargs['token']
        correct_token = token_creator(node._id, user._id, data)
        if correct_token != given_token:
            raise serializers.ValidationError("Incorrect token.")
        return data

    def create(self, validated_data):
        request = self.context['request']
        schema = MetaSchema.find(
            Q('name', 'eq', self.template)).sort('-schema_version')[0]
        user = request.user
        node = self.context['view'].get_node()
        formatted_data = {j: validated_data[j] for j in self.data_keys}
        registration = node.register_node(
            schema=schema,
            auth=Auth(user),
            template=self.template,
            data=json.dumps(process_payload(formatted_data))
        )
        return registration

class RegistrationOpenEndedSerializer(NodeSerializer):
    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(read_only=True)
    summary = ser.CharField(required=False, default='', write_only=True, help_text="Provide a narrative summary of what is contained in this registration, or how it differs from prior registrations.")
    registered_meta = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)
    category = ser.CharField(read_only=True)

    def validate(self, data):
        request = self.context['request']
        user = request.user
        node = self.context['view'].get_node()
        token = token_creator(node._id, user._id, data)
        url = absolute_reverse('nodes:node-registration-open-ended-token', kwargs={'pk': node._id, 'token': token})
        registration_warning = REGISTER_WARNING.format(_(node.title))
        raise serializers.ValidationError([registration_warning, url])

    class Meta:
        type_ = 'registrations'

class RegistrationOpenEndedWithTokenSerializer(RegistrationWithTokenMixin, RegistrationOpenEndedSerializer):
    template = "Open-Ended_Registration"
    data_keys = ['summary']

class RegistrationPreDataCollectionSerializer(NodeSerializer):
    TRUE_FALSE_CHOICES = ["Yes", "No"]

    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(read_only=True)
    registered_meta = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)
    category = ser.CharField(read_only=True)

    looked = ser.ChoiceField(choices=TRUE_FALSE_CHOICES, default='', required=False, help_text="Is data collection for this project underway or complete?", write_only=True)
    datacompletion = ser.ChoiceField(choices=TRUE_FALSE_CHOICES, default='', required=False, help_text="Have you looked at the data?", write_only=True)
    comments = ser.CharField(default='', required=False, help_text="Other Comments", write_only=True)

    def validate(self, data):
        request = self.context['request']
        user = request.user
        node = self.context['view'].get_node()
        token = token_creator(node._id, user._id, data)
        url = absolute_reverse('nodes:node-registration-pre-data-collection-token', kwargs={'pk': node._id, 'token': token})
        registration_warning = REGISTER_WARNING.format(_(node.title))
        raise serializers.ValidationError([registration_warning, url])

    class Meta:
        type_ = 'registrations'

class RegistrationPreDataCollectionWithTokenSerializer(RegistrationWithTokenMixin, RegistrationPreDataCollectionSerializer):
    template = "OSF-Standard_Pre-Data_Collection_Registration"
    data_keys = ['looked', 'datacompletion', 'comments']

class ReplicationRecipePreRegistrationSerializer(NodeSerializer):
    YES_NO_CHOICES = ["yes", "no"]
    SIM_DIFF_CHOICES = ["Exact", "Close", "Different"]

    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(read_only=True)
    registered_meta = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)
    category = ser.CharField(read_only=True)

    item1 = ser.CharField(default='', write_only=True, help_text="Verbal description of the effect I am trying to replicate")
    item2 = ser.CharField(default='', write_only=True, help_text="It is important to replicate this effect because")
    item3 = ser.CharField(default='', write_only=True, help_text="The effect size of the effect I am trying to replicate is")
    item4 = ser.CharField(default='', write_only=True, help_text="The confidence interval of the original effect is")
    item5 = ser.CharField(default='', write_only=True, help_text="The sample size of the original effect is")
    item6 = ser.CharField(default='', write_only=True, help_text="Where was the original study conducted? (e.g., lab, in the field, online)")
    item7 = ser.CharField(default='', write_only=True, help_text="What country/region was the original study conducted in?")
    item8 = ser.CharField(default='', write_only=True, help_text="What kind of sample did the original study use? (e.g., student, Mturk, representative)")
    item9 = ser.CharField(default='', write_only=True, help_text="Was the original study conducted with paper-and-pencil surveys, on a computer, or something else?")
    item10 = ser.ChoiceField(default='', write_only=True, choices=YES_NO_CHOICES, help_text="Are the original materials for the study available from the author?")
    item11 = ser.CharField(default='', write_only=True, help_text="I know that assumptions (e.g., about the meaning of the stimuli) in the original study will also hold in my replication because")
    item12 = ser.CharField(default='', write_only=True, help_text="Location of the experimenter during data collection")
    item13 = ser.CharField(default='', write_only=True, help_text="Experimenter knowledge of participant experimental condition")
    item14 = ser.CharField(default='', write_only=True, help_text="Experimenter knowledge of overall hypotheses")
    item15 = ser.CharField(default='', write_only=True, help_text="My target sample size is")
    item16 = ser.CharField(default='', write_only=True, help_text="The rationale for my sample size is")
    item17 = ser.ChoiceField(default='', write_only=True, choices=SIM_DIFF_CHOICES, help_text="The similarities/differences in the instructions are")
    item18 = ser.ChoiceField(default='', write_only=True, choices=SIM_DIFF_CHOICES, help_text="The similarities/differences in the measures are")
    item19 = ser.ChoiceField(default='', write_only=True, choices=SIM_DIFF_CHOICES, help_text="The similarities/differences in the stimuli are")
    item20 = ser.ChoiceField(default='', write_only=True, choices=SIM_DIFF_CHOICES, help_text="The similarities/differences in the procedure are")
    item21 = ser.ChoiceField(default='', write_only=True, choices=SIM_DIFF_CHOICES, help_text="The similarities/differences in the location (e.g., lab vs. online; alone vs. in groups) are")
    item22 = ser.ChoiceField(default='', write_only=True, choices=SIM_DIFF_CHOICES, help_text="The similarities/difference in remuneration are")
    item23 = ser.ChoiceField(default='', write_only=True, choices=SIM_DIFF_CHOICES, help_text="The similarities/differences between participant populations are")
    item24 = ser.CharField(default='', write_only=True, help_text="What differences between the original study and your study might be expected to influence the size and/or direction of the effect?")
    item25 = ser.CharField(default='', write_only=True, help_text="I have taken the following steps to test whether the differences listed in #22 will influence the outcome of my replication attempt")
    item26 = ser.CharField(default='', write_only=True, help_text="My exclusion criteria are (e.g., handling outliers, removing participants from analysis)")
    item27 = ser.CharField(default='', write_only=True, help_text="My analysis plan is (justify differences from the original)")
    item28 = ser.CharField(default='', write_only=True, help_text="A successful replication is defined as")

    def validate(self, data):
        request = self.context['request']
        user = request.user
        node = self.context['view'].get_node()
        token = token_creator(node._id, user._id, data)
        url = absolute_reverse('nodes:node-registration-pre-registration-token', kwargs={'pk': node._id, 'token': token})
        registration_warning = REGISTER_WARNING.format(_(node.title))
        raise serializers.ValidationError([registration_warning, url])

    class Meta:
        type_ = 'registrations'

class ReplicationRecipePreRegistrationWithTokenSerializer(RegistrationWithTokenMixin, ReplicationRecipePreRegistrationSerializer):
    template = "Replication_Recipe_(Brandt_et_al.,_2013):_Pre-Registration"
    data_keys = ["item" + str(j) for j in range(1, 29)]

class ReplicationRecipePostCompletionSerializer(NodeSerializer):
    EFFECT_SIZE = ["significantly different from the original effect size", "not significantly different from the original effect size"]
    REPLICATION_CONCLUSION = ["success", "informative failure to replicate", "practical failure to replicate", "inconclusive"]

    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(read_only=True)
    registered_meta = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)
    category = ser.CharField(read_only=True)

    item29 = ser.CharField(default='', write_only=True, help_text="The finalized materials, procedures, analysis plan etc of the replication are registered here")
    item30 = ser.CharField(default='', write_only=True, help_text="The effect size of the replication is")
    item31 = ser.CharField(default='', write_only=True, help_text="The confidence interval of the replication effect size is")
    item32 = ser.ChoiceField(default='', choices=EFFECT_SIZE, write_only=True, help_text="The replication effect size is")
    item33 = ser.ChoiceField(default='', choices=REPLICATION_CONCLUSION, write_only=True, help_text="I judge the replication to be a(n)")
    item34 = ser.CharField(default='', write_only=True, help_text="I judge it so because")
    item35 = ser.CharField(default='', write_only=True, help_text="Interested experts can obtain my data and syntax here")
    item36 = ser.CharField(default='', write_only=True, help_text="All of the analyses were reported in the report or are available here")
    item37 = ser.CharField(default='', write_only=True, help_text="The limitations of my replication study are")

    def validate(self, data):
        request = self.context['request']
        user = request.user
        node = self.context['view'].get_node()
        token = token_creator(node._id, user._id, data)
        url = absolute_reverse('nodes:node-registration-post-completion-token', kwargs={'pk': node._id, 'token': token})
        registration_warning = REGISTER_WARNING.format(_(node.title))
        raise serializers.ValidationError([registration_warning, url])

    class Meta:
        type_ = 'registrations'

class ReplicationRecipePostCompletionWithTokenSerializer(RegistrationWithTokenMixin, ReplicationRecipePostCompletionSerializer):
    template = "Replication_Recipe_(Brandt_et_al.,_2013):_Post-Completion"
    data_keys = ["item" + str(j) for j in range(29, 38)]

class NodePointersSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    node_id = ser.CharField(source='node._id', help_text='The ID of the node that this pointer points to')
    title = ser.CharField(read_only=True, source='node.title', help_text='The title of the node that this pointer '
                                                                         'points to')

    class Meta:
        type_ = 'pointers'

    links = LinksField({
        'html': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        pointer_node = Node.load(obj.node._id)
        return pointer_node.absolute_url

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        auth = Auth(user)
        node = self.context['view'].get_node()
        pointer_node = Node.load(validated_data['node']['_id'])
        pointer = node.add_pointer(pointer_node, auth, save=True)
        return pointer

    def update(self, instance, validated_data):
        pass

class NodeFilesSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    provider = ser.CharField(read_only=True)
    path = ser.CharField(read_only=True)
    item_type = ser.CharField(read_only=True)
    name = ser.CharField(read_only=True)
    metadata = ser.DictField(read_only=True)

    class Meta:
        type_ = 'files'

    links = LinksField({
        'self': WaterbutlerLink(kwargs={'node_id': '<node_id>'}),
        'self_methods': 'valid_self_link_methods',
        'related': Link('nodes:node-files', kwargs={'pk': '<node_id>'},
                        query_kwargs={'path': '<path>', 'provider': '<provider>'}),
    })

    @staticmethod
    def valid_self_link_methods(obj):
        return obj['valid_self_link_methods']

    def create(self, validated_data):
        # TODO
        pass

    def update(self, instance, validated_data):
        # TODO
        pass

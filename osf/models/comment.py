
import pytz
from django.db import models
from django.db.models import Q
from django.utils import timezone
from osf.models import Node
from osf.models import NodeLog
from osf.models.base import GuidMixin, Guid, BaseModel
from osf.models.mixins import CommentableMixin
from osf.models.spam import SpamMixin
from osf.models import validators

from framework.exceptions import PermissionsError
from osf.utils.fields import NonNaiveDateTimeField
from website import settings
from website.util import api_v2_url
from website.project import signals as project_signals
from website.project.model import get_valid_mentioned_users_guids


class Comment(GuidMixin, SpamMixin, CommentableMixin, BaseModel):
    __guid_min_length__ = 12
    OVERVIEW = 'node'
    FILES = 'files'
    WIKI = 'wiki'

    user = models.ForeignKey('OSFUser', null=True, on_delete=models.CASCADE)
    # the node that the comment belongs to
    node = models.ForeignKey('AbstractNode', null=True, on_delete=models.CASCADE)

    # The file or project overview page that the comment is for
    root_target = models.ForeignKey(Guid, on_delete=models.SET_NULL,
                                    related_name='comments',
                                    null=True, blank=True)

    # the direct 'parent' of the comment (e.g. the target of a comment reply is another comment)
    target = models.ForeignKey(Guid, on_delete=models.SET_NULL,
                                    related_name='child_comments',
                                    null=True, blank=True)

    date_created = NonNaiveDateTimeField(auto_now_add=True)
    date_modified = NonNaiveDateTimeField(auto_now=True)
    modified = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    # The type of root_target: node/files
    page = models.CharField(max_length=255, blank=True)
    content = models.TextField(
        validators=[validators.CommentMaxLength(settings.COMMENT_MAXLENGTH),
                    validators.string_required]
    )

    # The mentioned users
    ever_mentioned = models.ManyToManyField(blank=True, related_name='mentioned_in', to='OSFUser')

    @property
    def url(self):
        return '/{}/'.format(self._id)

    @property
    def absolute_api_v2_url(self):
        path = '/comments/{}/'.format(self._id)
        return api_v2_url(path)

    @property
    def target_type(self):
        """The object "type" used in the OSF v2 API."""
        return 'comments'

    @property
    def root_target_page(self):
        """The page type associated with the object/Comment.root_target."""
        return None

    def belongs_to_node(self, node_id):
        """Check whether the comment is attached to the specified node."""
        return self.node._id == node_id

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url

    def get_comment_page_url(self):
        if isinstance(self.root_target.referent, Node):
            return self.node.absolute_url
        return settings.DOMAIN + str(self.root_target._id) + '/'

    def get_content(self, auth):
        """ Returns the comment content if the user is allowed to see it. Deleted comments
        can only be viewed by the user who created the comment."""
        if not auth and not self.node.is_public:
            raise PermissionsError

        if self.is_deleted and ((not auth or auth.user.is_anonymous) or
                                (auth and not auth.user.is_anonymous and self.user._id != auth.user._id)):
            return None

        return self.content

    def get_comment_page_title(self):
        if self.page == Comment.FILES:
            return self.root_target.referent.name
        elif self.page == Comment.WIKI:
            return self.root_target.referent.page_name
        return ''

    def get_comment_page_type(self):
        if self.page == Comment.FILES:
            return 'file'
        elif self.page == Comment.WIKI:
            return 'wiki'
        return self.node.project_or_component

    @classmethod
    def find_n_unread(cls, user, node, page, root_id=None):
        if node.is_contributor(user):
            if page == Comment.OVERVIEW:
                view_timestamp = user.get_node_comment_timestamps(target_id=node._id)
                root_target = Guid.load(node._id)
            elif page == Comment.FILES or page == Comment.WIKI:
                view_timestamp = user.get_node_comment_timestamps(target_id=root_id)
                root_target = Guid.load(root_id)
            else:
                raise ValueError('Invalid page')

            if not view_timestamp.tzinfo:
                view_timestamp = view_timestamp.replace(tzinfo=pytz.utc)

            return cls.objects.filter(
                Q(node=node) & ~Q(user=user) & Q(is_deleted=False) &
                (Q(date_created__gt=view_timestamp) | Q(date_modified__gt=view_timestamp)) &
                Q(root_target=root_target)
            ).count()

        return 0

    @classmethod
    def create(cls, auth, **kwargs):
        comment = cls(**kwargs)
        if not comment.node.can_comment(auth):
            raise PermissionsError('{0!r} does not have permission to comment on this node'.format(auth.user))
        log_dict = {
            'project': comment.node.parent_id,
            'node': comment.node._id,
            'user': comment.user._id,
            'comment': comment._id,
        }
        if isinstance(comment.target.referent, Comment):
            comment.root_target = comment.target.referent.root_target
        else:
            comment.root_target = comment.target

        page = getattr(comment.root_target.referent, 'root_target_page', None)
        if not page:
            raise ValueError('Invalid root target.')
        comment.page = page

        log_dict.update(comment.root_target.referent.get_extra_log_params(comment))

        new_mentions = []
        if comment.content:
            if not comment.id:
                # must have id before accessing M2M
                comment.save()
            new_mentions = get_valid_mentioned_users_guids(comment, comment.node.contributors)
            if new_mentions:
                project_signals.mention_added.send(comment, new_mentions=new_mentions, auth=auth)
                comment.ever_mentioned.add(*comment.node.contributors.filter(guids___id__in=new_mentions))

        comment.save()

        comment.node.add_log(
            NodeLog.COMMENT_ADDED,
            log_dict,
            auth=auth,
            save=False,
        )

        comment.node.save()
        project_signals.comment_added.send(comment, auth=auth, new_mentions=new_mentions)

        return comment

    def edit(self, content, auth, save=False):
        if not self.node.can_comment(auth) or self.user._id != auth.user._id:
            raise PermissionsError('{0!r} does not have permission to edit this comment'.format(auth.user))
        log_dict = {
            'project': self.node.parent_id,
            'node': self.node._id,
            'user': self.user._id,
            'comment': self._id,
        }
        log_dict.update(self.root_target.referent.get_extra_log_params(self))
        self.content = content
        self.modified = True
        self.date_modified = timezone.now()
        new_mentions = get_valid_mentioned_users_guids(self, self.node.contributors)

        if save:
            if new_mentions:
                project_signals.mention_added.send(self, new_mentions=new_mentions, auth=auth)
                self.ever_mentioned.add(*self.node.contributors.filter(guids___id__in=new_mentions))
            self.save()
            self.node.add_log(
                NodeLog.COMMENT_UPDATED,
                log_dict,
                auth=auth,
                save=False,
            )
            self.node.save()

    def delete(self, auth, save=False):
        if not self.node.can_comment(auth) or self.user._id != auth.user._id:
            raise PermissionsError('{0!r} does not have permission to comment on this node'.format(auth.user))
        log_dict = {
            'project': self.node.parent_id,
            'node': self.node._id,
            'user': self.user._id,
            'comment': self._id,
        }
        self.is_deleted = True
        log_dict.update(self.root_target.referent.get_extra_log_params(self))
        self.date_modified = timezone.now()
        if save:
            self.save()
            self.node.add_log(
                NodeLog.COMMENT_REMOVED,
                log_dict,
                auth=auth,
                save=False,
            )
            self.node.save()

    def undelete(self, auth, save=False):
        if not self.node.can_comment(auth) or self.user._id != auth.user._id:
            raise PermissionsError('{0!r} does not have permission to comment on this node'.format(auth.user))
        self.is_deleted = False
        log_dict = {
            'project': self.node.parent_id,
            'node': self.node._id,
            'user': self.user._id,
            'comment': self._id,
        }
        log_dict.update(self.root_target.referent.get_extra_log_params(self))
        self.date_modified = timezone.now()
        if save:
            self.save()
            self.node.add_log(
                NodeLog.COMMENT_RESTORED,
                log_dict,
                auth=auth,
                save=False,
            )
            self.node.save()

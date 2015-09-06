
class TaggableMixin(object):

    @property
    def __node(self):
        from website.models import Node
        return self if isinstance(self, Node) else self.node

    def resolve_log(self, auth, tag, file_name=None, add_tag=True):
        from website.models import NodeLog
        from website.addons.base import GuidFile

        if isinstance(self, GuidFile):
            action = NodeLog.FILETAG_ADDED if add_tag else NodeLog.FILETAG_REMOVED
            params = {
                'node': self.__node._primary_key,
                'fileName': file_name,
                'tag': tag,
                'url': self.guid_url
            }
        else:
            action = NodeLog.TAG_ADDED if add_tag else NodeLog.TAG_REMOVED
            params = {
                'parent_node': self.__node.parent_id,
                'node': self.__node._primary_key,
                'tag': tag
            }

        self.__node.add_log(
            action=action,
            params=params,
            auth=auth,
            save=False
        )

    def add_tag(self, tag, auth, file_name=None):
        from website.models import Tag
        from website.addons.base import GuidFile

        if tag not in self.tags:
            new_tag = Tag.load(tag)
            if not new_tag:
                new_tag = Tag(_id=tag)
            new_tag.save()
            self.tags.append(new_tag)
            self.resolve_log(auth, tag=tag, file_name=file_name)
            if isinstance(self, GuidFile):
                self.__node.save()
            self.save()

    def remove_tag(self, tag, auth, file_name=None):
        from website.addons.base import GuidFile

        if tag in self.tags:
            self.tags.remove(tag)
            self.resolve_log(auth, tag=tag, file_name=file_name, add_tag=False)
            if isinstance(self, GuidFile):
                self.__node.save()
            self.save()

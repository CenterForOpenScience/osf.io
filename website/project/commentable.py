from abc import ABCMeta, abstractmethod, abstractproperty


class Commentable(object):
    __metaclass__ = ABCMeta

    def root_target_page(self):
        return False

    @abstractproperty
    def is_deleted(self):
        return False

    @abstractmethod
    def belongs_to_node(self, node):
        return False

import os
import itertools
from waterbutler.core import exceptions


class WaterButlerPathPart:
    DECODE = lambda x: x
    ENCODE = lambda x: x

    def __init__(self, part, _id=None):
        self._id = _id
        self._part = part

    @property
    def identifier(self):
        return self._id

    @property
    def value(self):
        return self.__class__.DECODE(self._part)

    @property
    def raw(self):
        return self._part

    @property
    def ext(self):
        return None  # Todo

    def increment_file_name(self):
        pass  # Todo

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self._part)


class WaterButlerPath:
    """
    A standardized and validated immutable WaterButler path.
    """

    PART_CLASS = WaterButlerPathPart

    @classmethod
    def generic_path_validation(cls, path):
        """Validates a WaterButler specific path, e.g. /folder/file.txt, /folder/
        :param str path: WaterButler path
        """
        if not path:
            raise exceptions.InvalidPathError('Must specify path')
        if not path.startswith('/'):
            raise exceptions.InvalidPathError('Invalid path \'{}\' specified'.format(path))
        if '//' in path:
            raise exceptions.InvalidPathError('Invalid path \'{}\' specified'.format(path))
        # Do not allow path manipulation via shortcuts, e.g. '..'
        absolute_path = os.path.abspath(path)
        if not path == '/' and path.endswith('/'):
            absolute_path += '/'
        if not path == absolute_path:
            raise exceptions.InvalidPathError('Invalid path \'{}\' specified'.format(absolute_path))

    @classmethod
    def validate_folder(cls, path):
        if not path.is_dir:
            raise exceptions.CreateFolderError('Path must be a directory', code=400)

        if path.is_root:
            raise exceptions.CreateFolderError('Path can not be root', code=400)

    @classmethod
    def from_parts(cls, parts, folder=False):
        _ids, _parts = [], ['']
        for part in parts:
            _ids.append(part.identifier)
            _parts.append(part.raw)

        return cls('/'.join(_parts), _ids=_ids, folder=folder)

    def __init__(self, path, _ids=(), prepend=None, folder=None):
        self.__class__.generic_path_validation(path)

        self._orig_path = path

        self._prepend = prepend

        if prepend:
            self._prepend_parts = [self.PART_CLASS(part, None) for part in prepend.rstrip('/').split('/')]
        else:
            self._prepend_parts = []

        self._parts = [
            self.PART_CLASS(part, _id)
            for _id, part in
            itertools.zip_longest(_ids, path.rstrip('/').split('/'))
        ]

        if folder is not None:
            self._is_folder = bool(folder)
        else:
            self._is_folder = self._orig_path.endswith('/')

        if self.is_dir and not self._orig_path.endswith('/'):
            self._orig_path += '/'

    @property
    def is_root(self):
        return len(self._parts) == 1

    @property
    def is_dir(self):
        return self._is_folder

    @property
    def is_file(self):
        return not self._is_folder

    @property
    def parts(self):
        return self._parts

    @property
    def name(self):
        return self._parts[-1].value

    @property
    def identifier(self):
        return self._parts[-1].identifier

    @property
    def path(self):
        return '/'.join([x.value for x in self.parts[1:]]) + ('/' if self.is_dir else '')

    @property
    def full_path(self):
        return '/'.join([x.value for x in self._prepend_parts + self.parts[1:]]) + ('/' if self.is_dir else '')

    @property
    def parent(self):
        if len(self.parts) == 1:
            return None
        return self.__class__.from_parts(self.parts[:-1], folder=True, prepend=self._prepend)

    def __str__(self):
        return '/'.join([x.raw for x in self.parts]) + ('/' if self.is_dir else '')

    def __repr__(self):
        return '{}({!r}, prepend={!r})'.format(self.__class__.__name__, self._orig_path, self._prepend)

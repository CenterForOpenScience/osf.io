from picklestorage import PickleStorage
from StringIO import StringIO
try:
    import cpickle as pickle
except ImportError:
    import pickle

class EphemeralStorage(PickleStorage):
    def __init__(self, *args, **kwargs):
        self.store = {}
        self.fp = StringIO()

    def flush(self):
        pickle.dump(self.store, self.fp, -1)

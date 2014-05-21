from types import ModuleType
from warnings import warn
import rpy2.rinterface as rinterface
import rpy2.robjects.lib
import conversion as conversion
from rpy2.robjects.functions import SignatureTranslatedFunction
from rpy2.robjects.constants import NULL
from rpy2.robjects import Environment

_require = rinterface.baseenv['require']
_as_env = rinterface.baseenv['as.environment']
_package_has_namespace = rinterface.baseenv['packageHasNamespace']
_system_file = rinterface.baseenv['system.file']
_get_namespace = rinterface.baseenv['getNamespace']
_get_namespace_version = rinterface.baseenv['getNamespaceVersion']
_get_namespace_exports = rinterface.baseenv['getNamespaceExports']
try:
    _find_package = rinterface.baseenv['find.package']
except LookupError:
    _find_package = rinterface.baseenv['.find.package']
_packages = rinterface.baseenv['.packages']
_libpaths = rinterface.baseenv['.libPaths']
_loaded_namespaces = rinterface.baseenv['loadedNamespaces']
_globalenv = rinterface.globalenv
_new_env = rinterface.baseenv["new.env"]

StrSexpVector = rinterface.StrSexpVector
_data = rinterface.baseenv['::'](StrSexpVector(('utils', )),
                                 StrSexpVector(('data', )))

_reval = rinterface.baseenv['eval']
_options = rinterface.baseenv['options']


def no_warnings(func):
    def run_withoutwarnings(*args, **kwargs):
        warn_i = _options().do_slot('names').index('warn')
        oldwarn = _options()[warn_i][0]
        _options(warn = -1)
        try:
            res = func(*args, **kwargs)
        except Exception, e:
            # restore the old warn setting before propagating
            # the exception up
            _options(warn = oldwarn)
            raise e
        _options(warn = oldwarn)
        return res
    return run_withoutwarnings

@no_warnings
def _eval_quiet(expr):
    return _reval(expr)

def reval(string, envir = _globalenv):
    """ Evaluate a string as R code
    - string: a string
    - envir: an environment in which the environment should take place
             (default: R's global environment)
    """
    p = rinterface.parse(string)
    res = _reval(p, envir = envir)
    return res

def quiet_require(name, lib_loc = None):
    """ Load an R package /quietly/ (suppressing messages to the console). """
    if lib_loc == None:
        lib_loc = "NULL"
    else:
        lib_loc = "\"%s\"" % (lib_loc.replace('"', '\\"'))
    expr_txt = "suppressPackageStartupMessages(base::require(%s, lib.loc=%s))" \
        %(name, lib_loc)
    expr = rinterface.parse(expr_txt)
    ok = _eval_quiet(expr)
    return ok

def get_packagepath(package):
    """ return the path to an R package installed """
    res = _find_package(rinterface.StrSexpVector((package, )))
    return res[0]


class PackageData(object):
    """ Datasets in an R package.
    In R datasets can be distributed with a package.

    Datasets can be:

    - serialized R objects

    - R code (that produces the dataset)

    For a given R packages, datasets are stored separately from the rest
    of the code and are evaluated/loaded lazily.

    The lazy aspect has been conserved and the dataset are only loaded
    or generated when called through the method 'fetch()'.
    """
    _packagename = None
    _lib_loc = None
    _datasets = None
    def __init__(self, packagename, lib_loc = rinterface.NULL):
        self._packagename = packagename
        self._lib_loc

    def _init_setlist(self):
        _datasets = dict()
        # 2D array of information about datatsets
        tmp_m = _data(**{'package':StrSexpVector((self._packagename, )),
                         'lib.loc': self._lib_loc})[2]
        nrows, ncols = tmp_m.do_slot('dim')
        c_i = 2
        for r_i in range(nrows):
            _datasets[tmp_m[r_i + c_i * nrows]] = None
            # FIXME: check if instance methods are overriden
        self._datasets = _datasets

    def names(self):
        """ Names of the datasets"""
        if self._datasets is None:
            self._init_setlist()
        return self._datasets.keys()
    
    def fetch(self, name):
        """ Fetch the dataset (loads it or evaluates the R associated
        with it.

        In R, datasets are loaded into the global environment by default
        but this function returns an environment that contains the dataset(s).
        """
        #tmp_env = rinterface.SexpEnvironment()
        if self._datasets is None:
            self._init_setlist()

        if name not in self._datasets:
            raise ValueError('Data set "%s" cannot be found' % name)
        env = _new_env()
        _data(StrSexpVector((name, )),
              **{'package': StrSexpVector((self._packagename, )),
                 'lib.loc': self._lib_loc,
                 'envir': env})
        return Environment(env)


class Package(ModuleType):
    """ Models an R package
    (and can do so from an arbitrary environment - with the caution
    that locked environments should mostly be considered).
     """
    
    _env = None
    __rname__ = None
    _translation = None
    _rpy2r = None
    __fill_rpy2r__ = None
    __update_dict__ = None
    _exported_names = None
    __version__ = None
    __rdata__ = None

    def __init__(self, env, name, translation = {}, 
                 exported_names = None, on_conflict = 'fail',
                 version = None):
        """ Create a Python module-like object from an R environment,
        using the specified translation if defined. 

        - on_conflict: 'fail' or 'warn' (default: 'fail')
        """

        super(Package, self).__init__(name)
        self._env = env
        self.__rname__ = name
        self._translation = translation
        mynames = tuple(self.__dict__)
        self._rpy2r = {}
        if exported_names is None:
            exported_names = set(self._env.keys())
        self._exported_names = exported_names
        self.__fill_rpy2r__(on_conflict = on_conflict)
        self._exported_names = self._exported_names.difference(mynames)
        self.__version__ = version
                
    def __update_dict__(self, on_conflict = 'fail'):
        """ Update the __dict__ according to what is in the R environment """
        for elt in self._rpy2r:
            del(self.__dict__[elt])
        self._rpy2r.clear()
        self.__fill_rpy2r__(on_conflict = on_conflict)

    def __fill_rpy2r__(self, on_conflict = 'fail'):
        """ Fill the attribute _rpy2r.

        - on_conflict: 'fail' or 'warn' (default: 'fail')
        """

        assert(on_conflict in ('fail', 'warn'))

        name = self.__rname__
        for rname in self._env:
            if rname in self._translation:
                rpyname = self._translation[rname]
            else:
                dot_i = rname.find('.')
                if dot_i > -1:
                    rpyname = rname.replace('.', '_')
                    if rpyname in self._rpy2r:
                        msg = ('Conflict when converting R symbol'+\
                                   ' in the package "%s"' +\
                                   ' to a Python symbol ' +\
                                   '(%s -> %s while there is already'+\
                                   ' %s)') %(self.__rname__,
                                             rname, rpyname,
                                             rpyname)
                        if on_conflict == 'fail':
                            raise LibraryError(msg)
                        else:
                            warn(msg)
                            continue
                else:
                    rpyname = rname
                if rpyname in self.__dict__ or rpyname == '__dict__':
                    raise LibraryError('The symbol ' + rname +\
                                       ' in the package "' + name + '"' +\
                                       ' is conflicting with ' +\
                                       'a Python object attribute')
            self._rpy2r[rpyname] = rname
            if (rpyname != rname) and (rname in self._exported_names):
                self._exported_names.remove(rname)
                self._exported_names.add(rpyname)
            rpyobj = conversion.ri2py(self._env[rname])
            if hasattr(rpyobj, '__rname__'):
                rpyobj.__rname__ = rname
            #FIXME: shouldn't the original R name be also in the __dict__ ?
            self.__dict__[rpyname] = rpyobj


    def __repr__(self):
        s = super(Package, self).__repr__()
        return 'rpy2.robjecs.packages.Package as a ' + s

class SignatureTranslatedPackage(Package):
    def __fill_rpy2r__(self, on_conflict = 'fail'):
        super(SignatureTranslatedPackage, self).__fill_rpy2r__(on_conflict = on_conflict)
        for name, robj in self.__dict__.iteritems():
            if isinstance(robj, rinterface.Sexp) and robj.typeof == rinterface.CLOSXP:
                self.__dict__[name] = SignatureTranslatedFunction(self.__dict__[name])
                

class SignatureTranslatedAnonymousPackage(SignatureTranslatedPackage):
    def __init__(self, string, name):
        env = Environment()
        reval(string, env)
        super(SignatureTranslatedAnonymousPackage, self).__init__(env,
                                                                  name)

class LibraryError(ImportError):
    """ Error occuring when importing an R library """
    pass



def importr(name, 
            lib_loc = None,
            robject_translations = {}, 
            signature_translation = True,
            suppress_messages = True,
            on_conflict = 'fail',
            data = True):
    """ Import an R package.

    Arguments:

    - name: name of the R package

    - lib_loc: specific location for the R library (default: None)

    - robject_translations: dict (default: {})

    - signature_translation: dict (default: {})

    - suppress_message: Suppress messages R usually writes on the console
      (defaut: True)

    - on_conflict: 'fail' or 'warn' (default: 'fail')

    - data: embed a PackageData objects under the attribute 
      name __rdata__ (default: True)

    Return:

    - an instance of class SignatureTranslatedPackage, or of class Package 

    """

    rname = rinterface.StrSexpVector((name, ))

    if suppress_messages:
        ok = quiet_require(name, lib_loc = lib_loc)
    else:
        ok = _require(rinterface.StrSexpVector(rname), 
                      **{'lib.loc': rinterface.StrSexpVector((lib_loc, ))})[0]
    if not ok:
        raise LibraryError("The R package %s could not be imported" %name)
    if _package_has_namespace(rname, 
                              _system_file(package = rname)):
        env = _get_namespace(rname)
        version = _get_namespace_version(rname)[0]
        exported_names = set(_get_namespace_exports(rname))
    else:
        env = _as_env(rinterface.StrSexpVector(['package:'+name, ]))
        exported_names = None
        version = None
    if signature_translation:
        pack = SignatureTranslatedPackage(env, name, 
                                          translation = robject_translations,
                                          exported_names = exported_names,
                                          on_conflict = on_conflict,
                                          version = version)
    else:
        pack = Package(env, name, translation = robject_translations,
                       exported_names = exported_names,
                       on_conflict = on_conflict,
                       version = version)
    if data:
        if pack.__rdata__ is not None:
            warn('While importing the R package "%s", the rpy2 Package object is masking a translated R symbol "__rdata__" already present' % name)
        pack.__rdata__ = PackageData(name, lib_loc = lib_loc)

    return pack


def wherefrom(symbol, startenv = rinterface.globalenv):
    """ For a given symbol, return the environment
    this symbol is first found in, starting from 'startenv'
    """
    env = startenv
    obj = None
    tryagain = True
    while tryagain:
        try:
            obj = env[symbol]
            tryagain = False
        except LookupError, knf:
            env = env.enclos()
            if env.rsame(rinterface.emptyenv):
                tryagain = False
            else:
                tryagain = True
    return conversion.ri2py(env)


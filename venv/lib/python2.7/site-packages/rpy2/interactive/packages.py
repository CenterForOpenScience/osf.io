from rpy2.robjects.packages import importr as _importr
import rpy2.robjects.help as rhelp
from rpy2.rinterface import baseenv
from os import linesep
from collections import OrderedDict
import re

class Packages(object):
    __instance = None
    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __setattr__(self, name, value):
        raise AttributeError("Attributes cannot be set. Use 'importr'")

packages = Packages()
_loaded_namespaces = baseenv['loadedNamespaces']

def importr(packname, newname = None, verbose = False):
    """ Wrapper around rpy2.robjects.packages.importr, 
    adding the following features:
    
    - package instance added to the pseudo-module 'packages'

    - automatic pydoc generation from the R help pages

    """

    assert isinstance(packname, str)
    packinstance = _importr(packname, on_conflict = 'warn')

    # fix the package name (dots possible in R package names)
    if newname is None:
        newname = packname.replace('.', '_')

    Packages().__dict__[newname] = packinstance

    ## Currently too slow for a serious usage: R's introspection 
    ## of S4 classes is not fast enough
    # d = {}
    # for cn in methods.get_classnames(packname):
    #     class AutoS4(RS4):
    #         __metaclass__ = methods.RS4Auto_Type
    #         __rpackagename__ = packname
    #         __rname__ = cn
    #     newcn = cn.replace('.', '_')
    #     d[newcn] = AutoS4
    # S4Classes().__dict__[newname] = d 
    
    p_latex_code = re.compile('\\\\code{([^}]+)}')
    p_latex_link = re.compile('\\\\link{([^}]+)}')
    p_latex_any_curly = re.compile('\\\\[^ ]+{([^}]+)}')
    p_latex_any = re.compile('\\\\([^ ]+)')
    p_latex_usage = re.compile('\\\\method{(?P<method>[^}]+)}{(?P<class>[^}]+)}(?P<signature>.+)')

    doc = rhelp.Package(packname)
    for obj_name in packinstance.__dict__:
        obj = packinstance.__dict__[obj_name]
        # ignore class-defined attributes to only consider
        # the ones defined dynamically
        if hasattr(type(packinstance), obj_name):
            continue
        try:
            p = doc.fetch(obj.__rname__)
        except rhelp.HelpNotFoundError as hnfe:
            # No R documentation could be found for the object
            if verbose:
                print('Pydoc generator: no help for "%s"' %(obj_name, ))
            continue
        except AttributeError as ae:
            # No __rname__ for the object
            print('Pydoc generator: oddity with "%s"' %(obj_name, ))
            continue
        except:
            print('Pydoc generator: oddity with "%s" ("%s")' %(obj_name, obj.__rname__))
            continue

        if obj_name in packinstance._exported_names:
            exported = True
        else:
            exported = False
            #if verbose:
            #    print('Pydoc generator: "%s" not exported' %(obj_name, ))
            #continue

        docstring = [p.title(), 
                     '[ %s - %s exported ]' %(p._type, 'not' if not exported else ''), 
                     '** Experimental dynamic conversion of the associated R documentation **']

        tmp = p.description()
        tmp = re.sub(p_latex_any_curly, "'\\1'", tmp)
        docstring.append(tmp)
        docstring.append('')

        tmp_usage = p.usage().split(linesep)
        for i, row in enumerate(tmp_usage):
            tmp_m = p_latex_usage.match(row)
            if tmp_m is not None:
                tmp_usage[i] = '%s_%s%s' %(tmp_m.group('method'), 
                                           tmp_m.group('class'),
                                           tmp_m.group('signature'))
        tmp_usage = linesep.join(tmp_usage)
        docstring.extend([tmp_usage, ''])


        if obj_name not in packinstance._exported_names:
            tmp = p.seealso()
            tmp = re.sub(p_latex_code, "'\\1'", tmp)
            tmp = re.sub(p_latex_any_curly, '\\1', tmp)
            tmp = re.sub(p_latex_any, "'\\1'", tmp)
            docstring.extend(['', 'See Also:', tmp])
            docstring = linesep.join(docstring)
            obj.__doc__ = docstring
            continue


        try:
            arguments = p.arguments()
        except KeyError as ke:
            #FIXME: no arguments - should the handling differ a bit ?
            arguments = tuple()
        # Assume uniqueness of values in the dict. This is making sense since
        # parameters to the function should have unique names ans... this appears to be enforced
        # by R when declaring a function

        arguments = OrderedDict(arguments)

        if hasattr(obj, '_prm_translate'):
            docstring.extend(['', 'Parameters:', ''])
            for k, v in obj._prm_translate.items():
                try:
                    tmp = arguments[v]
                    tmp = re.sub(p_latex_code, "'\\1'", tmp)
                    tmp = re.sub(p_latex_any_curly, '\\1', tmp)
                    tmp = re.sub(p_latex_any, "'\\1'", tmp)
                    docstring.append('%s -- %s' %(k, tmp))
                except KeyError:
                    # This is an inconsistency in the R documentation
                    # (the parameter in the function's signature does
                    # not have an entry in the R documentation).
                    # Do nothing.
                    # 
                    if verbose:
                        print('Pydoc generator: no help for parameter "%s" in %s' %(k, obj_name))
                    docstring.append('%s -- [error fetching the documentation]' %(k))
                    #print('Pydoc generator: oddity with R\'s "%s" over the parameter "%s"' %(obj_name, v))

        tmp = p.value()
        tmp = re.sub(p_latex_code, "'\\1'", tmp)
        tmp = re.sub(p_latex_any, '\\1', tmp)

        docstring.extend(['', 'Returns:', tmp])
        tmp = p.seealso()
        tmp = re.sub(p_latex_code, "'\\1'", tmp)
        tmp = re.sub(p_latex_any_curly, '\\1', tmp)
        tmp = re.sub(p_latex_any, "'\\1'", tmp)
        docstring.extend(['', 'See Also:', tmp])
        docstring = linesep.join(docstring)
        obj.__doc__ = docstring
    return packinstance

for packname in _loaded_namespaces():
    importr(packname)

import os, sys
import tempfile
import rpy2.rinterface

rpy2.rinterface.initr()

import conversion

class RObjectMixin(object):
    """ Class to provide methods common to all RObject instances """
    __rname__ = None

    __tempfile = rpy2.rinterface.baseenv.get("tempfile")
    __file = rpy2.rinterface.baseenv.get("file")
    __fifo = rpy2.rinterface.baseenv.get("fifo")
    __sink = rpy2.rinterface.baseenv.get("sink")
    __close = rpy2.rinterface.baseenv.get("close")
    __readlines = rpy2.rinterface.baseenv.get("readLines")
    __unlink = rpy2.rinterface.baseenv.get("unlink")
    __rclass = rpy2.rinterface.baseenv.get("class")
    __rclass_set = rpy2.rinterface.baseenv.get("class<-")
    __show = rpy2.rinterface.baseenv.get("show")

    def __str__(self):
        if sys.platform == 'win32':
            tmpf = tempfile.NamedTemporaryFile(delete=False)
            tfname = tmpf.name
            tmp = self.__file(rpy2.rinterface.StrSexpVector([tfname,]),
                              open=rpy2.rinterface.StrSexpVector(["r+", ]))
            self.__sink(tmp)
        else:
            writeconsole = rpy2.rinterface.get_writeconsole()
            s = []
            def f(x):
                s.append(x)
            rpy2.rinterface.set_writeconsole(f)
        self.__show(self)
        if sys.platform == 'win32':
            self.__sink()
            s = tmpf.readlines()
            tmpf.close()
            try:
                del tmpf
                os.unlink(tfname)
            except WindowsError:
                if os.path.exists(tfname):
                    print 'Unable to unlink tempfile %s' % tfname
            s = str.join(os.linesep, s)
        else:
            rpy2.rinterface.set_writeconsole(writeconsole)
            s = str.join('', s)
        return s

    def r_repr(self):
        """ String representation for an object that can be
        directly evaluated as R code.
        """
        return repr_robject(self, linesep='\n')

    def _rclass_get(self):
        try:
            res = self.__rclass(self)
            #res = conversion.ri2py(res)
            return res
        except rpy2.rinterface.RRuntimeError, rre:
            if self.typeof == rpy2.rinterface.SYMSXP:
                #unevaluated expression: has no class
                return (None, )
            else:
                raise rre
    def _rclass_set(self, value):
        res = self.__rclass_set(self, value)
        self.__sexp__ = res.__sexp__
            
    rclass = property(_rclass_get, _rclass_set, None,
                      "R class for the object, stored as an R string vector.")


def repr_robject(o, linesep=os.linesep):
    s = rpy2.rinterface.baseenv.get("deparse")(o)
    s = str.join(linesep, s)
    return s



class RObject(RObjectMixin, rpy2.rinterface.Sexp):
    """ Base class for all R objects. """
    def __setattr__(self, name, value):
        if name == '_sexp':
            if not isinstance(value, rpy2.rinterface.Sexp):
                raise ValueError("_attr must contain an object " +\
                                     "that inherits from rpy2.rinterface.Sexp" +\
                                     "(not from %s)" %type(value))
        super(RObject, self).__setattr__(name, value)


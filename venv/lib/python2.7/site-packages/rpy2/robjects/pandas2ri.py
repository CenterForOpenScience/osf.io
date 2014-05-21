import rpy2.robjects as ro
import rpy2.robjects.conversion as conversion
import rpy2.rinterface as rinterface
from rpy2.rinterface import SexpVector, INTSXP

from pandas.core.frame import DataFrame as PandasDataFrame
from pandas.core.series import Series as PandasSeries
from pandas.core.index import Index as PandasIndex

from collections import OrderedDict
from rpy2.robjects.vectors import DataFrame, Vector, ListVector, StrVector, IntVector, POSIXct

# pandas is requiring numpy. We add the numpy conversion as implicit
import rpy2.robjects.numpy2ri as numpy2ri
numpy2ri.activate()

original_conversion = conversion.py2ri

ISOdatetime = rinterface.baseenv['ISOdatetime']

def pandas2ri(obj):
    if isinstance(obj, PandasDataFrame):
        od = OrderedDict()
        for name, values in obj.iteritems():
            if values.dtype.kind == 'O':
                od[name] = StrVector(values)
            else:
                od[name] = ro.conversion.py2ri(values)
        return DataFrame(od)
    elif isinstance(obj, PandasIndex):
        if obj.dtype.kind == 'O':
            return StrVector(obj)
        else:
            # only other alternative to 'O' is integer, I think
            return original_conversion(obj)        
    elif isinstance(obj, PandasSeries):
        if obj.dtype == '<M8[ns]':
            # time series
            d = [IntVector([x.year for x in obj]),
                 IntVector([x.month for x in obj]),
                 IntVector([x.day for x in obj]),
                 IntVector([x.hour for x in obj]),
                 IntVector([x.minute for x in obj]),
                 IntVector([x.second for x in obj])]
            res = ISOdatetime(*d)
            #FIXME: can the POSIXct be created from the POSIXct constructor ?
            # (is '<M8[ns]' mapping to Python datetime.datetime ?)
            res = POSIXct(res)
        else:
            # converted as a numpy array
            res = original_conversion(obj) 
        # "index" is equivalent to "names" in R
        if obj.ndim == 1:
            res.names = ListVector({'x': ro.conversion.py2ri(obj.index)})
        else:
            res.dimnames = ListVector(ro.conversion.py2ri(obj.index))
        return res
    else:
        return original_conversion(obj) 

def ri2pandas(o):
    if isinstance(o, DataFrame):
        raise NotImplementedError("Conversion from rpy2 DataFrame to pandas' DataFrame")
    else:
        res = ro.default_ri2py(o)
    return res

def activate():
    conversion.py2ri = pandas2ri
    conversion.ri2py = ri2pandas 


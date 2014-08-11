import os.path
import pandas as pd
import xlrd
# rpy2 is an optional dependency, but it is needed for SPSS rendering to work.
rpy2_available = True
try:
    import rpy2.robjects as robjects
    from rpy2.rinterface import RRuntimeError
    import pandas.rpy.common as com
except ImportError:
    rpy2_available = False

from .base import TabularRenderer
from .exceptions import TooBigTableError, BlankOrCorruptTableError, StataVersionError

from .utilities import MAX_COLS, MAX_ROWS
from pandas.parser import CParserError
from xlrd.biffh import XLRDError


class CSVRenderer(TabularRenderer):
    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext.lower() == ".csv"

    def _build_df(self, file_pointer):
        try:
            return {"dataframe": pd.read_csv(file_pointer)}
        except CParserError:
            raise BlankOrCorruptTableError("Is this a valid csv file?")


class STATARenderer(TabularRenderer):
    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext.lower() == ".dta"

    def _build_df(self, file_pointer):
        try:
            return {"dataframe":pd.read_stata(file_pointer)}
        except (ValueError, TypeError, KeyError):
            raise StataVersionError("Version of given Stata file is not 104, 105, 108, 113 (Stata 8/9), 114 (Stata 10/11) or 115 (Stata 12)")


class ExcelRenderer(TabularRenderer):
    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext.lower() in [".xls", ".xlsx"]

    def _build_df(self, file_pointer):
        workbook = xlrd.open_workbook(file_pointer.name)
        sheets = workbook.sheet_names()
        sheet = workbook.sheet_by_name(sheets[0])
        if sheet.ncols > MAX_COLS or sheet.nrows > MAX_ROWS:
            raise TooBigTableError("Too many rows or columns")


        retdic = {}
        num_sheets = len(sheets)

        if num_sheets > 1:
            retdic['message'] = "File contains {0} sheets. Only the first is displayed. Download the file to view all of them.".format(num_sheets)
        try:
            retdic['dataframe'] = pd.read_excel(file_pointer, sheets[0])
            return retdic
        except (IndexError, XLRDError):
            raise BlankOrCorruptTableError("Is this a valid excel file?")


class SPSSRenderer(TabularRenderer):
    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext.lower() == ".sav"

    def _build_df(self, file_pointer):
        if not rpy2_available:
            return {'dataframe': None}
        try:
            r = robjects
            r.r("require(foreign)")
            r.r('x <- read.spss("{}",to.data.frame=T)'.format(file_pointer.name))
            r.r('row.names(x) = 0:(nrow(x)-1)')
            return {"dataframe": com.load_data('x')}
        except (RRuntimeError, TypeError):
            raise BlankOrCorruptTableError("Is this a valid SPSS file?")

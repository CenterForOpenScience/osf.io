import os.path
import pandas as pd
import xlrd
import rpy2.robjects as robjects
import pandas.rpy.common as com
from .base import TabularRenderer
from .utilities import TooBigError, MAX_COLS, MAX_ROWS


class CSVRenderer(TabularRenderer):
    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext.lower() == ".csv"

    def _build_df(self, file_pointer):
        return pd.read_csv(file_pointer)


class STATARenderer(TabularRenderer):
    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext.lower() == ".dta"

    def _build_df(self, file_pointer):
        return pd.read_stata(file_pointer)


class ExcelRenderer(TabularRenderer):
    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext.lower() in [".xls", ".xlsx"]

    def _build_df(self, file_pointer):
        workbook = xlrd.open_workbook(file_pointer.name)
        sheets = workbook.sheet_names()
        sheet = workbook.sheet_by_name(sheets[0])
        if sheet.ncols > MAX_COLS or sheet.nrows > MAX_ROWS:
            raise TooBigError
        return pd.read_excel(file_pointer, sheets[0])


class SPSSRenderer(TabularRenderer):
    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext.lower() == ".sav"

    def _build_df(self, file_pointer):
        r = robjects
        r.r("require(foreign)")
        r.r('x <- read.spss("{}",to.data.frame=T)'.format(file_pointer.name))
        r.r('row.names(x) = 0:(nrow(x)-1)')
        return com.load_data('x')
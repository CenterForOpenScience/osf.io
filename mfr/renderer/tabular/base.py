import os
import json
from struct import error
from .. import FileRenderer
from .utilities import column_population, row_population, check_shape, MAX_COLS, MAX_ROWS, TooBigError
from pandas.parser import CParserError
from rpy2.rinterface import RRuntimeError
from xlrd.biffh import XLRDError



class TabularRenderer(FileRenderer):
    def _render(self, file_pointer, **kwargs):
        _, file_name = os.path.split(file_pointer.name)
        _, ext = os.path.splitext(file_name)

        try:
            dataframe = self._build_df(file_pointer)
        except TooBigError:
            return """
                <div>Unable to render; download file to view it: </div>
                <div> oo many rows or columns</div>
                <div>Max rows x cols: {max_rows} x {max_cols} </div>
                """.format(
                max_rows=MAX_ROWS,
                max_cols=MAX_COLS,
            )

        except (IndexError, CParserError):
            return """
                <div>Unable to render; download file to view it: </div>
                <div>Is this file blank?</div>
                """

        except ValueError:
            if ext == ".dta":
                return """
                <div>Unable to render; download file to view it: </div>
                <div>Version of given Stata file is not 104, 105, 108, 113 (Stata 8/9), 114 (Stata 10/11) or 115 (Stata 12) </div>
                <div>Is this a valid Stata file?</div>
                    """
            else:
                raise Exception

        except (RRuntimeError, error, XLRDError):
            return """
                <div>Unable to render; download file to view it: </div>
                <div>Is this a valid {ext} file?</div><br>
                    """.format(ext=ext)

        if dataframe is None:
            return """
        <div>Unable to render; download file to view it: </div>
        <div>Is it a valid {ext} file?</div><br>
        <div>Is it empty?</div>
        """.format(file_name=file_name, ext=ext)

        try:
            check_shape(dataframe)
        except TooBigError:
            return """
                <div>Unable to render; download file to view it: </div>
                <div>Too many rows or columns</div>
                <div>Max rows x cols: {max_rows} x {max_cols} </div>
                """.format(
                max_rows=MAX_ROWS,
                max_cols=MAX_COLS,

            )

        columns = column_population(dataframe)
        rows = row_population(dataframe)
        return self._render_mako(
            "tabular.mako",
            columns=json.dumps(columns),
            rows=json.dumps(rows),
            STATIC_PATH=self.STATIC_PATH,
        )
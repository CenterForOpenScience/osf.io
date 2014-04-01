import os
import json
from .. import FileRenderer
from .utilities import column_population, row_population, check_shape, MAX_COLS, MAX_ROWS
from .exceptions import BlankOrCorruptTableError, TooBigTableError


class TabularRenderer(FileRenderer):
    def _render(self, file_pointer, **kwargs):
        _, file_name = os.path.split(file_pointer.name)
        _, ext = os.path.splitext(file_name)

        returned = self._build_df(file_pointer)
        dataframe = returned['dataframe']

        if dataframe is None:
            raise BlankOrCorruptTableError("Is this a valid instance of this file type?")

        if check_shape(dataframe):
            raise TooBigTableError("Too many rows or columns")

        columns = json.dumps(column_population(dataframe))
        rows = json.dumps(row_population(dataframe))

        return self._render_mako(
            "tabular.mako",
            writing=returned.get('message', ""),
            columns=columns,
            rows=rows,
            STATIC_PATH=self.STATIC_PATH,
        )
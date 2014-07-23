from .. import FileRenderer


class PdbRenderer(FileRenderer):

    def _detect(self, fp):
        fname = fp.name
        for ext in ['pdb']:
            if fname.endswith(ext):
                return True
        return False

    def _render(self, file_pointer, url=None, **kwargs):
        return self._render_mako(
            'pdb.mako',
            pdb_file=file_pointer.read(),
            STATIC_PATH=self.STATIC_PATH,
        )

    def export_pdb(self, fp):
        return fp.read(), '.pdb'

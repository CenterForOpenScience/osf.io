from jinja2 import Environment, PackageLoader
from pydocx.DocxParser import EMUS_PER_PIXEL

templates = {
    'delete': 'text_delete.xml',
    'drawing': 'drawing.xml',
    'hyperlink': 'hyperlink.xml',
    'insert': 'insert.xml',
    'linebreak': 'linebreak.xml',
    'main': 'base.xml',
    'numbering': 'numbering.xml',
    'p': 'p.xml',
    'pict': 'pict.xml',
    'r': 'r.xml',
    'rpr': 'rpr.xml',
    'sdt': 'sdt.xml',
    'sectPr': 'sectPr.xml',
    'smartTag': 'smart_tag.xml',
    'style': 'style.xml',
    'styles': 'styles.xml',
    't': 't.xml',
    'table': 'table.xml',
    'tc': 'tc.xml',
    'tr': 'tr.xml',
}

env = Environment(
    loader=PackageLoader(
        'pydocx.tests',
        'templates',
    ),
)


class DocxBuilder(object):

    @classmethod
    def xml(self, body):
        template = env.get_template(templates['main'])
        return template.render(body=body)

    @classmethod
    def p_tag(
            self,
            text,
            style='style0',
            jc=None,
    ):
        if isinstance(text, str):
            # Use create a single r tag based on the text and the bold
            run_tag = DocxBuilder.r_tag(
                [DocxBuilder.t_tag(text)],
            )
            run_tags = [run_tag]
        elif isinstance(text, list):
            run_tags = text
        else:
            run_tags = [self.r_tag([])]
        template = env.get_template(templates['p'])

        kwargs = {
            'run_tags': run_tags,
            'style': style,
            'jc': jc,
        }
        return template.render(**kwargs)

    @classmethod
    def linebreak(self):
        template = env.get_template(templates['linebreak'])
        kwargs = {}
        return template.render(**kwargs)

    @classmethod
    def t_tag(self, text):
        template = env.get_template(templates['t'])
        kwargs = {
            'text': text,
        }
        return template.render(**kwargs)

    @classmethod
    def r_tag(
            self,
            elements,
            rpr=None,
    ):
        template = env.get_template(templates['r'])
        if rpr is None:
            rpr = DocxBuilder.rpr_tag()
        kwargs = {
            'elements': elements,
            'rpr': rpr,
        }
        return template.render(**kwargs)

    @classmethod
    def rpr_tag(self, inline_styles=None, *args, **kwargs):
        if inline_styles is None:
            inline_styles = {}
        valid_styles = (
            'b',
            'i',
            'u',
            'caps',
            'smallCaps',
            'strike',
            'dstrike',
            'vanish',
            'webHidden',
            'vertAlign',
        )
        for key in inline_styles:
            if key not in valid_styles:
                raise AssertionError('%s is not a valid style' % key)
        template = env.get_template(templates['rpr'])
        kwargs = {
            'tags': inline_styles,
        }
        return template.render(**kwargs)

    @classmethod
    def hyperlink_tag(self, r_id, run_tags):
        template = env.get_template(templates['hyperlink'])
        kwargs = {
            'r_id': r_id,
            'run_tags': run_tags,
        }
        return template.render(**kwargs)

    @classmethod
    def insert_tag(self, run_tags):
        template = env.get_template(templates['insert'])
        kwargs = {
            'run_tags': run_tags,
        }
        return template.render(**kwargs)

    @classmethod
    def delete_tag(self, deleted_texts):
        template = env.get_template(templates['delete'])
        kwargs = {
            'deleted_texts': deleted_texts,
        }
        return template.render(**kwargs)

    @classmethod
    def smart_tag(self, run_tags):
        template = env.get_template(templates['smartTag'])
        kwargs = {
            'run_tags': run_tags,
        }
        return template.render(**kwargs)

    @classmethod
    def sdt_tag(self, p_tag):
        template = env.get_template(templates['sdt'])
        kwargs = {
            'p_tag': p_tag,
        }
        return template.render(**kwargs)

    @classmethod
    def li(self, text, ilvl, numId, bold=False):
        if isinstance(text, str):
            # Use create a single r tag based on the text and the bold
            run_tag = DocxBuilder.r_tag([DocxBuilder.t_tag(text)], bold)
            run_tags = [run_tag]
        elif isinstance(text, list):
            run_tags = []
            for run_text, run_bold in text:
                run_tags.append(
                    DocxBuilder.r_tag(
                        [DocxBuilder.t_tag(run_tags)],
                        run_bold,
                    ),
                )
        else:
            raise AssertionError('text must be a string or a list')
        template = env.get_template(templates['p'])

        kwargs = {
            'run_tags': run_tags,
            'is_list': True,
            'ilvl': ilvl,
            'numId': numId,
        }
        return template.render(**kwargs)

    @classmethod
    def table_cell(self, paragraph, merge=False, merge_continue=False):
        kwargs = {
            'paragraph': paragraph,
            'merge': merge,
            'merge_continue': merge_continue
        }
        template = env.get_template(templates['tc'])
        return template.render(**kwargs)

    @classmethod
    def table_row(self, tcs):
        template = env.get_template(templates['tr'])
        return template.render(table_cells=tcs)

    @classmethod
    def table(self, trs):
        template = env.get_template(templates['table'])
        return template.render(table_rows=trs)

    @classmethod
    def drawing(self, r_id, height=None, width=None):
        template = env.get_template(templates['drawing'])
        if height is not None:
            height = height * EMUS_PER_PIXEL
        if width is not None:
            width = width * EMUS_PER_PIXEL
        kwargs = {
            'r_id': r_id,
            'height': height,
            'width': width,
        }
        return template.render(**kwargs)

    @classmethod
    def pict(self, r_id=None, height=None, width=None):
        template = env.get_template(templates['pict'])
        kwargs = {
            'r_id': r_id,
            'height': height,
            'width': width,
        }
        return template.render(**kwargs)

    @classmethod
    def sectPr_tag(self, p_tag):
        template = env.get_template(templates['sectPr'])

        kwargs = {
            'p_tag': p_tag,
        }
        return template.render(**kwargs)

    @classmethod
    def styles_xml(self, style_tags):
        template = env.get_template(templates['styles'])

        kwargs = {
            'style_tags': style_tags,
        }
        return template.render(**kwargs)

    @classmethod
    def style(self, style_id, value):
        template = env.get_template(templates['style'])

        kwargs = {
            'style_id': style_id,
            'value': value,
        }

        return template.render(**kwargs)

    @classmethod
    def numbering(self, numbering_dict):
        template = env.get_template(templates['numbering'])

        kwargs = {
            'numbering_dict': numbering_dict,
        }

        return template.render(**kwargs)

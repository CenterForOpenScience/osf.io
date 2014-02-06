from .. import FileRenderer
import os.path
import pygments
import pygments.lexers
import pygments.formatters


KNOWN_EXTENSIONS = ['.rb',
 '.cs',
 '.ahk',
 '.rs',
 '.c9search_results',
 '.scm',
 '.vhd',
 '.vbs',
 '.twig',
 '.jack',
 '.jl',
 '.js',
 '.matlab',
 '.tcl',
 '.dot',
 '.plg',
 '.clj',
 '.Rd',
 '.pl',
 '.ejs',
 '.scad',
 '.lisp',
 '.py',
 '.cpp',
 '.snippets',
 '.css',
 '.vm',
 '.groovy',
 '.liquid',
 '.xq',
 '.proto',
 '.php',
 '.asm',
 '.sh',
 '.curly',
 '.hs',
 '.hx',
 '.tex',
 '.sjs',
 '.mysql',
 '.html',
 '.space',
 '.haml',
 '.CBL',
 '.styl',
 '.ada',
 '.lucene',
 '.pas',
 '.tmSnippet',
 '.ps1',
 '.yaml',
 '.soy',
 '.sass',
 '.scala',
 '.scss',
 '.ini',
 '.bat',
 '.glsl',
 '.diff',
 '.frt',
 '.less',
 '.erl',
 '.erb',
 '.toml',
 '.hbs',
 '.m',
 '.sql',
 '.json',
 '.d',
 '.lua',
 '.as',
 '.nix',
 '.txt',
 '.r',
 '.v',
 '.jade',
 '.go',
 '.ts',
 '.md',
 '.jq',
 '.mc',
 '.xml',
 '.Rhtml',
 '.ml',
 '.dart',
 '.pgsql',
 '.coffee',
 '.lp',
 '.ls',
 '.jsx',
 '.asciidoc',
 '.jsp',
 '.logic',
 '.properties',
 '.textile',
 '.lsl',
 '.abap',
 '.ftl',
 '.java',
 '.cfm']



class CodeRenderer(FileRenderer):
    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext in KNOWN_EXTENSIONS

    def _render(self, file_pointer, url):
        formatter = pygments.formatters.HtmlFormatter()
        content = file_pointer.read()
        highlight = pygments.highlight(
            content, pygments.lexers.guess_lexer_for_filename(
                file_pointer.name, content), formatter)
        link = 'href="{}/code/css/style.css" />'.format(self.STATIC_PATH)
        return '<link rel="stylesheet"' + link + '\n' + highlight


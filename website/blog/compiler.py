#
# Copyright (c) 2015 Will Bond, Mjumbe Wawatu Ukweli, 2012 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, version 3 only.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# GNU Lesser General Public License version 3 (see the file LICENSE).

"""The compiler for ghostpy."""


__all__ = [
    'Compiler',
    'strlist',
    'Scope'
    ]

__metaclass__ = type

import re
import sys
import bleach
from types import ModuleType
import linecache
from datetime import datetime
from urllib import quote
from collections import OrderedDict
from BeautifulSoup import BeautifulSoup
import os.path

import ghostpy
import copy
import ghostpy._templates
from pymeta.grammar import OMeta

# This allows the code to run on Python 2 and 3 by
# creating a consistent reference for the appropriate
# string class
try:
    str_class = unicode
except NameError:
    # Python 3 support
    str_class = str


# Flag for testing
debug = False


# Note that unless we presume handlebars is only generating valid html, we have
# to accept anything - so a broken template won't be all that visible - it will
# just render literally (because the anything rule matches it).

# this grammar generates a tokenised tree
handlebars_grammar = r"""

template ::= (<text> | <templatecommand>)*:body => ['template'] + body
text ::= <newline_text> | <whitespace_text> | <other_text>
newline_text ::= (~(<start>) ('\r'?'\n'):char) => ('newline', u'' + char)
whitespace_text ::= (~(<start>) (' '|'\t'))+:text => ('whitespace', u''.join(text))
other_text ::= (~(<start>) <anything>)+:text => ('literal', u''.join(text))
other ::= <anything>:char => ('literal', u'' + char)
templatecommand ::= <blockrule>
    | <comment>
    | <escapedexpression>
    | <expression>
    | <partial>
start ::= '{' '{'
finish ::= '}' '}'
comment ::= <start> '!' (~(<finish>) <anything>)* <finish> => ('comment', )
space ::= ' '|'\t'|'\r'|'\n'
arguments ::= (<space>+ (<kwliteral>|<literal>|<path>|<subexpression>))*:arguments => arguments
subexpression ::= '(' <spaces> <path>:p (<space>+ (<kwliteral>|<literal>|<path>|<subexpression>))*:arguments <spaces> ')' => ('subexpr', p, arguments)
expression_inner ::= <spaces> <path>:p <arguments>:arguments <spaces> <finish> => (p, arguments)
expression ::= <start> '{' <expression_inner>:e '}' => ('expand', ) + e
    | <start> '&' <expression_inner>:e => ('expand', ) + e
escapedexpression ::= <start> <expression_inner>:e => ('escapedexpand', ) + e
block_inner ::= <spaces> <symbol>:s <arguments>:args <spaces> <finish>
    => (u''.join(s), args)
partial_inner ::= <spaces> <partialname>:s <arguments>:args <spaces> <finish>
    => (u''.join(s), args)
alt_inner ::= <spaces> ('^' | 'e' 'l' 's' 'e') <spaces> <finish>
partial ::= <start> '>' <partial_inner>:i => ('partial',) + i
path ::= ~('/') <pathseg>+:segments => ('path', segments)
kwliteral ::= <safesymbol>:s '=' (<literal>|<path>|<subexpression>):v => ('kwparam', s, v)
literal ::= (<string>|<integer>|<boolean>|<null>|<undefined>):thing => ('literalparam', thing)
string ::= '"' <notdquote>*:ls '"' => u'"' + u''.join(ls) + u'"'
    | "'" <notsquote>*:ls "'" => u"'" + u''.join(ls) + u"'"
integer ::= '-'?:sign <digit>+:ds => int((sign if sign else '') + ''.join(ds))
boolean ::= <false>|<true>
false ::= 'f' 'a' 'l' 's' 'e' => False
true ::= 't' 'r' 'u' 'e' => True
null ::= ('n' 'u' 'l' 'l') => None
undefined ::= ('u' 'n' 'd' 'e' 'f' 'i' 'n' 'e' 'd') => None
notdquote ::= <escapedquote>
    | '\n' => '\\n'
    | '\r' => '\\r'
    | '\\' => '\\\\'
    | (~('"') <anything>)
notsquote ::= <escapedquote>
    | '\n' => '\\n'
    | '\r' => '\\r'
    | '\\' => '\\\\'
    | (~("'") <anything>)
escapedquote ::= '\\' '"' => '\\"'
    | "\\" "'" => "\\'"
notclosebracket ::= (~(']') <anything>)
safesymbol ::=  ~<alt_inner> '['? (<letter>|'_'):start (<letterOrDigit>|'_')+:symbol ']'? => start + u''.join(symbol)
symbol ::=  ~<alt_inner> '['? (<letterOrDigit>|'-'|'@')+:symbol ']'? => u''.join(symbol)
partialname ::= ~<alt_inner> ('['|'"')? (~(<space>|<finish>|']'|'"' ) <anything>)+:symbol (']'|'"')? => u''.join(symbol)
pathseg ::= '[' <notclosebracket>+:symbol ']' => u''.join(symbol)
    | ('@' '.' '.' '/') => u'@@_parent'
    | <symbol>
    | '/' => u''
    | ('.' '.' '/') => u'@_parent'
    | '.' => u''
pathfinish :expected ::= <start> '/' <path>:found ?(found == expected) <finish>
symbolfinish :expected ::= <start> '/' <symbol>:found ?(found == expected) <finish>
blockrule ::= <start> '#' <block_inner>:i
      <template>:t <alttemplate>:alt_t <symbolfinish i[0]> => ('block',) + i + (t, alt_t)
    | <start> '^' <block_inner>:i
      <template>:t <alttemplate>:alt_t <symbolfinish i[0]> => ('invertedblock',) + i + (t, alt_t)
alttemplate ::= (<start> <alt_inner> <template>)?:alt_t => alt_t or []
"""

# this grammar compiles the template to python
compile_grammar = """
compile ::= <prolog> <rule>* => builder.finish()
prolog ::= "template" => builder.start()
rule ::= <literal>
    | <expand>
    | <escapedexpand>
    | <comment>
    | <block>
    | <invertedblock>
    | <partial>
block ::= [ "block" <anything>:symbol [<arg>*:arguments] [<compile>:t] [<compile>?:alt_t] ] => builder.add_block(symbol, arguments, t, alt_t)
comment ::= [ "comment" ]
literal ::= [ ( "literal" | "newline" | "whitespace" ) :value ] => builder.add_literal(value)
expand ::= [ "expand" <path>:value [<arg>*:arguments]] => builder.add_expand(value, arguments)
escapedexpand ::= [ "escapedexpand" <path>:value [<arg>*:arguments]] => builder.add_escaped_expand(value, arguments)
invertedblock ::= [ "invertedblock" <anything>:symbol [<arg>*:arguments] [<compile>:t] ] => builder.add_invertedblock(symbol, arguments, t, alt_t)
partial ::= ["partial" <anything>:symbol [<arg>*:arguments]] => builder.add_partial(symbol, arguments)
path ::= [ "path" [<pathseg>:segment]] => ("simple", segment)
 | [ "path" [<pathseg>+:segments] ] => ("complex", segments)
complexarg ::= [ "path" [<pathseg>+:segments] ] => ([u"resolve(context, '"  + u"', '".join(segments) + u"')"], segments)
    | [ "subexpr" ["path" <pathseg>:name] [<arg>*:arguments] ] => u'resolve_subexpr(helpers, "' + name + '", context' + (u', ' + u', '.join(arguments) if arguments else u'') + u')'
    | [ "literalparam" <anything>:value ] => {str_class}(value)
arg ::= [ "kwparam" <anything>:symbol <complexarg>:a ] => {str_class}(symbol) + '=' + a
    | <complexarg>
pathseg ::= "/" => ''
    | "." => ''
    | "" => ''
    | "this" => ''
pathseg ::= <anything>:symbol => u''.join(symbol)
"""
compile_grammar = compile_grammar.format(str_class=str_class.__name__)


class PybarsError(Exception):

    pass


class strlist(list):

    """A quasi-list to let the template code avoid special casing."""

    def __str__(self):  # Python 3
        return ''.join(self)

    def __unicode__(self):  # Python 2
        return u''.join(self)

    def grow(self, thing):
        """Make the list longer, appending for unicode, extending otherwise."""
        if type(thing) == str_class:
            self.append(thing)

        # This will only ever match in Python 2 since str_class is str in
        # Python 3.
        elif type(thing) == str:
            self.append(unicode(thing))

        else:
            # Recursively expand to a flat list; may deserve a C accelerator at
            # some point.
            for element in thing:
                self.grow(element)


_map = {
    '&': '&amp;',
    '"': '&quot;',
    "'": '&#x27;',
    '`': '&#x60;',
    '<': '&lt;',
    '>': '&gt;',
    }


def substitute(match, _map=_map):
    return _map[match.group(0)]


_escape_re = re.compile(r"&|\"|'|`|<|>")


def escape(something, _escape_re=_escape_re, substitute=substitute):
    return _escape_re.sub(substitute, something)


def pick(context, name, default=None):
    if isinstance(name, str) and hasattr(context, name):
        return getattr(context, name)
    if hasattr(context, 'get'):
        return context.get(name)
    try:
        return context[name]
    except (KeyError, TypeError):
        return default


sentinel = object()


class Scope:

    def __init__(self, context, parent, root, overrides=None, index=None, key=None, first=None, last=None, columns=None):
        self.context = context
        self.parent = parent
        self.root = root
        # Must be dict of keys and values
        self.overrides = overrides
        self.index = index
        self.key = key
        self.first = first
        self.last = last
        self.columns = columns

    def get(self, name, default=None):
        if name == '@blog':
            return self.root
        if name == '@_parent':
            return self.parent
        if name == '@index' and self.index is not None:
            return self.index
        if name == '@key' and self.key is not None:
            return self.key
        if name == '@first' and self.first is not None:
            return self.first
        if name == '@last' and self.last is not None:
            return self.last
        if name == '@odd' and self.index is not None:
            return (self.index % 2 == 0)
        if name == '@even' and self.index is not None:
            return (self.index % 2 == 1)
        if name == '@rowStart' and self.columns is not None and self.index is not None:
            return (self.index % self.columns == 0)
        if name == '@rowEnd' and self.columns is not None and self.index is not None:
            return (self.index % self.columns == (self.columns - 1))
        if name == 'this':
            return self.context
        if self.overrides and name in self.overrides:
            return self.overrides[name]
        return pick(self.context, name, default)
    __getitem__ = get

    def __len__(self):
        return len(self.context)

    # Added for Python 3
    def __str__(self):
        return str(self.context)

    # Only called in Python 2
    def __unicode__(self):
        return unicode(self.context)


def resolve(context, *segments):
    carryover_data = False

    # This makes sure that bare "this" paths don't return a Scope object
    if segments == ('',) and isinstance(context, Scope):
        return context.get('this')

    for segment in segments:

        # Handle @../index syntax by popping the extra @ along the segment path
        if carryover_data:
            carryover_data = False
            segment = u'@%s' % segment
        if len(segment) > 1 and segment[0:2] == '@@':
            segment = segment[1:]
            carryover_data = True

        if context is None:
            return None
        if segment in (None, ""):
            continue
        if type(context) in (list, tuple):
            offset = int(segment)
            context = context[offset]
        elif isinstance(context, Scope):
            context = context.get(segment)
        else:
            context = pick(context, segment)
    return context


def resolve_subexpr(helpers, name, context, *args, **kwargs):
    if name not in helpers:
        raise PybarsError(u"Could not find property %s" % (name,))
    return helpers[name](context, *args, **kwargs)


def prepare(value, should_escape):
    """
    Prepares a value to be added to the result

    :param value:
        The value to add to the result

    :param should_escape:
        If the string should be HTML-escaped

    :return:
        A unicode string or strlist
    """

    if value is None:
        return u''
    type_ = type(value)
    if type_ is not strlist:
        if type_ is not str_class:
            if type_ is bool:
                value = u'true' if value else u'false'
            else:
                value = str_class(value)
        if should_escape:
            value = escape(value)
    return value


def ensure_scope(context, root):
    return context if isinstance(context, Scope) else Scope(context, context, root)


def _author(*args, **kwargs):
    return args[0].get('author').get('name')


def _author_block(this, options, *args, **kwargs):
    return options['fn'](this)


def _blockHelperMissing(this, options, context, scope):
    if hasattr(context, '__call__'):
        context = context(this)
    if context != u"" and not context:
        return options['inverse'](this)
    if type(context) in (list, strlist, tuple):
        return _each(this, options, context)
    if context is True:
        callwith = this
    else:
        _ghostpy_['scope'] = scope
        options['fn'].keywords['scope'] = scope
        callwith = context
    return options['fn'](callwith)


def _content(*args, **kwargs):
    if kwargs.get('words') is not None:
        input_string=args[0].get('content')
        p = re.compile(r'<[^<]*?>')
        words=p.sub('', input_string).split(' ')
        words=filter(lambda a: a != '', words)
        s=words[:int(kwargs.get('words'))]

        temp=input_string
        k=' '.join(s).count(s[-1])
        i=1
        j=0
        while i<=k:
            l = temp.find(s[-1])
            j+=l +len(s[-1])
            temp=temp[l+len(s[-1]):]
            i+=1
        output_string=input_string[:j]
        content = BeautifulSoup(output_string)
    elif kwargs.get('characters') is not None:
        input_string=args[0].get('content')
        p = re.compile(r'<[^<]*?>')
        stripped = p.sub('', input_string)
        i = int(kwargs.get('characters'))
        if stripped[i-1] == ' ':
            end = i
        else:
            end = i + stripped[i:].index(' ')
        s = stripped[:end].split(' ')
        s = filter(lambda a: a != '', s)

        temp=input_string
        k=' '.join(s).count(s[-1])
        i=1
        j=0
        while i<=k:
            l = temp.find(s[-1])
            j+=l +len(s[-1])
            temp=temp[l+len(s[-1]):]
            i+=1
        output_string=input_string[:j]
        content = BeautifulSoup(output_string)

    else:
        content = args[0].get('content')
    return str(content)


def _date(*args, **kwargs):
    date_ = args[0].get('date')
    if date_ is None:
        date = datetime.today()
    else:
        date_ = " ".join(date_.split(" ")[:-2])
        date = datetime.strptime(date_, '%a %b %d %Y %X')
    format = kwargs.get('format')
    dict = OrderedDict([
        ("YYYY", "%Y"),
        ("YY", "%y"),
        ("MMMM", "%B"),
        ("MMM", "%b"),
        ("MM", "%m"),
        ("M", "%-m"),
        ("DD", "%d"),
        ("D", "%-d")
    ])
    for entry in dict:
        format = format.replace(entry, dict[entry])
    return datetime.strftime(date, format)


def _each(this, options, context):
    result = strlist()

    # All sequences in python have a length
    try:
        last_index = len(context) - 1

        # If there are no items, we want to trigger the else clause
        if last_index < 0:
            raise IndexError()

    except (TypeError, IndexError):
        return options['inverse'](this)

    # We use the presence of a keys method to determine if the
    # key attribute should be passed to the block handler
    has_keys = hasattr(context, 'keys')

    index = 0
    for value in context:
        kwargs = {
            'index': index,
            'first': index == 0,
            'last': index == last_index
        }

        if has_keys:
            kwargs['key'] = value
            value = context[value]

        scope = Scope(value, this, options['root'], **kwargs)
        result.grow(options['fn'](scope))

        index += 1

    return result


def _encode(*args, **kwargs):
    return quote(args[1])


def _excerpt(this, *args, **kwargs):
    tags = []
    attr = {}
    styles = []
    strip = True

    content = str(bleach.clean(this.get('content'),
                        tags=tags,
                        attributes=attr,
                        styles=styles,
                        strip=strip))

    if "words" in kwargs.keys():
        words = content.split()
        excerpt = " ".join(words[:int(kwargs.get("words"))])

    elif "characters" in kwargs.keys():
        chars = int(kwargs.get('characters'))
        last = content.find(' ', chars)
        excerpt = content[:last]

    else:
        words = content.split()
        excerpt = " ".join(words[:50])
    return excerpt


def _for_each(this, options, context, scope, columns=None):
    result = strlist()

    if columns is not None:
        columns = int(columns)

    # All sequences in python have a length
    try:
        last_index = len(context) - 1

        # If there are no items, we want to trigger the else clause
        if last_index < 0:
            raise IndexError()

    except (TypeError, IndexError):
        return options['inverse'](this)

    # We use the presence of a keys method to determine if the
    # key attribute should be passed to the block handler
    has_keys = hasattr(context, 'keys')

    index = 0
    for value in context:
        kwargs = {
            'index': index,
            'first': index == 0,
            'last': index == last_index,
            'columns': columns
        }

        if has_keys:
            kwargs['key'] = value
            value = context[value]

        scope_ = Scope(value, this, options['root'], **kwargs)
        _ghostpy_['scope'] = scope
        options['fn'].keywords['scope'] = scope
        try:
            result.grow(options['fn'](scope_))
        except TypeError:
            pass
        index += 1

    return result


def _ghost_head(*args, **kwargs):
    return ""


def _ghost_foot(*args, **kwargs):
    return "<script type='text/javascript' src='public/jquery.js'></script>"


def _has(this, options, **kwargs):
    tag_list_ = kwargs.get('tag')
    if tag_list_ is not None:
        tag_list = tag_list_.split(', ')
    else:
        tag_list = None
    author_list_ = kwargs.get('author')
    if author_list_ is not None:
        author_list = author_list_.split(', ')
    else:
        author_list = None
    tags_ = this.get('tags')
    if tags_ is not None:
        tags = []
        for tag in tags_:
            tags.append(tag.get('name'))

    author = this.get('author').get('name')

    tags_ok = False
    author_ok = False

    if tag_list is not None:
        for tag in tag_list:
            if tag in tags:
                tags_ok = True
                break

    if author_list is not None:
        for name in author_list:
            if name == author:
                author_ok = True
                break

    if tags_ok or author_ok:
        return options['fn'](this)
    else:
        return options['inverse'](this)


def _helperMissing(scope, name, *args):
    if not args:
        return None
    raise PybarsError(u"Could not find property %s" % (name,))


def _if(this, options, context):
    if hasattr(context, '__call__'):
        context = context(this)
    if context:
        return options['fn'](this)
    else:
        return options['inverse'](this)


def _is(this, options, list):
    context_list_ = list
    context_list = context_list_.split(', ')
    context = _ghostpy_.get('context')
    common = set(context_list) & set(context)
    count = len(common)
    if count >= 1:
        return options['fn'](this)
    else:
        return options['inverse'](this)

def _log(this, context):
    ghostpy.log(context)


def _lookup(this, context, key):
    try:
        return context[key]
    except (KeyError, IndexError, TypeError):
        return


def _page_url(*args, **kwargs):
    if args[0]['page'] is 1:
        return "./" + str(args[2])
    else:
        return "../" + str(args[2])


def _plural(*args, **kwargs):
    if args[1] == 0:
        return kwargs.get("empty")
    elif args[1] == 1:
        return kwargs.get("singular")
    elif args[1] > 1:
        return kwargs.get("plural")


def _post_class(*args, **kwargs):
    classes = ["post"]
    if args[0].get('featured'):
        classes.append("featured")
    tags = args[0].get('tags')
    if tags is not None:
        for tag in tags:
            classes.append("tag-" + tag.get('id'))
    return " ".join(classes)

def _tags(*args, **kwargs):
    tags = args[0].get('tags')
    separator = kwargs.get('separator')
    autolink = kwargs.get('autolink')
    prefix = kwargs.get('prefix')
    suffix = kwargs.get('suffix')
    if separator == None:
        separator = ", "

    if prefix == None:
        prefix = ""
    else:
        prefix = prefix + " "

    if suffix == None:
        suffix = ""
    else:
        suffix = " " + suffix

    if autolink == None:
        autolink = "True"

    html = []
    if tags is not None:
        for tag in tags:
            if autolink in ["True", "true"]:
                html.append("<a href='" + tag.get('url') + "'>" + tag.get('name') + "</a>")
            elif autolink in ["False", "false"]:
                html.append(tag.get('name'))
    html = separator.join(html)
    html = prefix + html + suffix
    return html


def _unless(this, options, context):
    if not context:
        return options['fn'](this)
    else:
        return options['inverse'](this)

def _url(*args, **kwargs):
    scope = args[1]
    context = _ghostpy_['context']
    absolute = False
    if kwargs.get('absolute') in ['True', 'true']:
        absolute = True
    route = ''
    url = ''

    if 'index' in context:
        if scope is 'root':
            if _ghostpy_['root']['pagination']['page'] is 1:
                route = "./"
            else:
                route = "../"

        if scope is 'post' or scope is 'next_post' or scope is 'prev_post' or scope is 'posts':
            file = args[0].get('file')
            if _ghostpy_['root']['pagination']['page'] is 1:
                route = "./post/" + file
            else:
                route = "../post/" + file

        if scope is 'navigation':
            route = "<undefined>"

        if scope is 'author':
            route = "<undefined>"

        if scope is 'tag':
            route = "<undefined>"

    if 'post' in context:
        if scope is 'root':
            route = "../../"

        if scope is 'post' or scope is 'next_post' or scope is 'prev_post':
            file = args[0].get('file')
            if absolute:
                route = _ghostpy_['base']+"/post/"+file
            else: return "../" + file

        if scope is 'navigation':
            route = "<undefined>"

        if scope is 'author':
            route = "<undefined>"

        if scope is 'tag':
            route = "<undefined>"

    return route


def _with(this, options, context):
    return options['fn'](context)


# scope for the compiled code to reuse globals
_ghostpy_defaults = {
    'helpers': {
        '_author': _author,
        'blockHelperMissing': _blockHelperMissing,
        'content': _content,
        'date': _date,
        'each': _each,
        'encode': _encode,
        'excerpt': _excerpt,
        'foreach': _for_each,
        'ghost_head': _ghost_head,
        'ghost_foot': _ghost_foot,
        'has': _has,
        'helperMissing': _helperMissing,
        'if': _if,
        'is': _is,
        'log': _log,
        'lookup': _lookup,
        'page_url': _page_url,
        'plural': _plural,
        'post_class': _post_class,
        'tags': _tags,
        'unless': _unless,
        'url': _url,
        'with': _with
    },
    'partials': {},
    'theme': 'casper',
    'blog_dict': {},
    'context': [],
    'scope': None,
    'root': None,
    'base': ''
}

_ghostpy_ = copy.deepcopy(_ghostpy_defaults)

def reset():
    return copy.deepcopy(_ghostpy_defaults)


class FunctionContainer:

    """
    Used as a container for functions by the CodeBuidler
    """

    def __init__(self, name, code):
        self.name = name
        self.code = code

    @property
    def full_code(self):
        nav_default = '<ul class="nav">{{#foreach navigation}}<li class="nav-{{slug}}{{#if current}} nav-current{{/if}}" role="presentation"><a href="{{url absolute="true"}}">{{label}}</a></li>{{/foreach}}</ul>'
        pag_default = '<nav class="pagination" role="navigation">{{#if prev}}<a class="newer-posts" href="{{page_url prev}}">&larr; Newer Posts</a>{{/if}}<span class="page-number">Page {{page}} of {{pages}}</span>{{#if next}}<a class="older-posts" href="{{page_url next}}">Older Posts &rarr;</a>{{/if}}</nav>'
        headers = (
            u'import ghostpy\n'
            u'\n'
            u'if ghostpy.__version__ != %s:\n'
            u'    raise ghostpy.PybarsError("This template was precompiled with pybars3 version %s, running version %%s" %% ghostpy.__version__)\n'
            u'\n'
            u'from ghostpy import strlist, Scope, PybarsError\n'
            u'from ghostpy._compiler import Compiler, _ghostpy_, escape, resolve, resolve_subexpr, prepare, ensure_scope\n'
            u'\n'
            u'from functools import partial\n'
            u'\n'
            u'\n'
            u'def _partial(path, context, helpers, partials, root):\n'
            u"    compiler = Compiler(_ghostpy_['theme'])\n"
            u"    if path != 'navigation' and path != 'pagination':\n"
            u"        with open(path) as hbs:\n"
            u"            source = hbs.read().decode('unicode-escape')\n"
            u"    elif path == 'navigation':\n"
            u"        source = u'%s'\n"
            u"    elif path == 'pagination':\n"
            u"        source = u'%s'\n"
            # u"    import pdb; pdb.set_trace()\n"
            u"    template = compiler.compile(source)\n"
            u"    output = template(context)\n"
            u"    return output\n"
            u'\n'
            u'\n'
        ) % (repr(ghostpy.__version__), ghostpy.__version__, nav_default, pag_default)

        return headers + self.code


class CodeBuilder:

    """Builds code for a template."""

    def __init__(self):
        self._reset()

    def _reset(self):
        self.stack = []
        self.var_counter = 1
        self.render_counter = 0

    def start(self):
        function_name = 'render' if self.render_counter == 0 else 'block_%s' % self.render_counter
        self.render_counter += 1

        self.stack.append((strlist(), {}, function_name))
        self._result, self._locals, _ = self.stack[-1]
        # Context may be a user hash or a Scope (which injects '@_parent' to
        # implement .. lookups). The JS implementation uses a vector of scopes
        # and then interprets a linear walk-up, which is why there is a
        # disabled test showing arbitrary complex path manipulation: the scope
        # approach used here will probably DTRT but may be slower: reevaluate
        # when profiling.
        if len(self.stack) == 1:
            self._result.grow([
                u"def render(context, helpers=None, partials=None, root=None):\n"
                u"    if _ghostpy_['scope'] is None:\n"
                u"        scope = 'root'\n"
                u"    else:\n"
                u"        scope = _ghostpy_['scope']\n"
                u"    if _ghostpy_['root'] is None:\n"
                u"        _ghostpy_['root'] = context\n"
                u"        root = context\n"
                u"    else:\n"
                u"        root = _ghostpy_['root']\n"
                u"    _helpers = dict(_ghostpy_['helpers'])\n"
                u"    _partials = dict(_ghostpy_['partials'])\n"
                u"    if helpers is not None:\n"
                u"        _helpers.update(helpers)\n"
                u"    helpers = _helpers\n"
                u"    if partials is not None:\n"
                u"        _partials.update(partials)\n"
                u"    partials = _partials\n"
                u"    called = root is None\n"
                u"    if called:\n"
                u"        root = context\n"
            ])
        else:
            self._result.grow(u"def %s(context, scope, helpers, partials, root):\n" % function_name)
        self._result.grow(u"    result = strlist()\n")
        self._result.grow(u"    context = ensure_scope(context, root)\n")

    def finish(self):
        lines, ns, function_name = self.stack.pop(-1)

        # Ensure the result is a string and not a strlist
        if len(self.stack) == 0:
            self._result.grow(u"    if called:\n")
            self._result.grow(u"        result = %s(result)\n" % str_class.__name__)
        self._result.grow(u"    return %s(result)\n" % str_class.__name__)

        source = str_class(u"".join(lines))

        self._result = self.stack and self.stack[-1][0]
        self._locals = self.stack and self.stack[-1][1]

        code = ''
        for key in ns:
            if isinstance(ns[key], FunctionContainer):
                code += ns[key].code + '\n'
            else:
                code += '%s = %s\n' % (key, repr(ns[key]))
        code += source

        result = FunctionContainer(function_name, code)
        if debug and len(self.stack) == 0:
            print('Compiled Python')
            print('---------------')
            print(result.full_code)

        return result

    def _wrap_nested(self, name):
        return u"partial(%s, scope=scope, helpers=helpers, partials=partials, root=root)" % name

    def add_block(self, symbol, arguments_, nested, alt_nested):
        if len(arguments_) > 0 and type(arguments_[0]) is tuple:
            (arguments, scope) = arguments_[0]
        else:
            arguments = arguments_
        name = nested.name
        self._locals[name] = nested

        if alt_nested:
            alt_name = alt_nested.name
            self._locals[alt_name] = alt_nested

        call = self.arguments_to_call(arguments)
        self._result.grow([
            u"    options = {'fn': %s}\n" % self._wrap_nested(name),
            u"    options['helpers'] = helpers\n"
            u"    options['partials'] = partials\n"
            u"    options['root'] = root\n"
            ])
        if alt_nested:
            self._result.grow([
                u"    options['inverse'] = ",
                self._wrap_nested(alt_name),
                u"\n"
                ])
        else:
            self._result.grow([
                u"    options['inverse'] = lambda this: None\n"
                ])
        if symbol == 'foreach' or symbol == 'each':
            if len(arguments_) == 2:
                (key, value) = tuple(arguments_[1].split('='))
                assert key == 'columns'
            else:
                value = "None"
            self._result.grow([
                u"    value = resolve(context, '%s')\n" % scope[0],
                u"    value = helpers['%s'](context, options, value, '%s', columns=%s)\n" % (symbol, scope[0], value),
                u"    result.grow(value or '')\n"
            ])
        else:
            self._result.grow([
                u"    value = helper = helpers.get('%s')\n" % symbol,
                u"    if value is None:\n"
                u"        value = resolve(context, '%s')\n" % symbol,
                u"    if helper and hasattr(helper, '__call__'):\n"
                u"        value = helper(context, options%s\n" % call,
                u"    else:\n"
                u"        value = helpers['blockHelperMissing'](context, options, value, '%s')\n" % symbol,
                u"    result.grow(value or '')\n"
                ])

    def add_literal(self, value):
        self._result.grow(u"    result.append(%s)\n" % repr(value))

    def _lookup_arg(self, arg):
        if not arg:
            return u"context"
        return arg

    def arguments_to_call(self, arguments):
        params = list(map(self._lookup_arg, arguments))
        output = u', '.join(params) + u')'
        if len(params) > 0:
            output = u', ' + output
        return output

    def find_lookup(self, path, path_type, call, segments=None):
        if path == "navigation" or path == "pagination":
            self.add_partial(path, [])
        else:
            if path == "author":
                path = "_author"
            if path_type == "simple":  # simple names can reference helpers.
                # TODO: compile this whole expression in the grammar; for now,
                # fugly but only a compile time overhead.
                # XXX: just rm.
                realname = path.replace('.get("', '').replace('")', '')
                self._result.grow([
                    u"    value = helpers.get('%s')\n" % realname,
                    u"    if value is None:\n"
                    u"        value = resolve(context, '%s')\n" % path,
                    u"    if hasattr(value, '__call__'):\n"
                    u"        value = value(context, scope%s\n" % call,
                    ])
            else:
                realname = None
                self._result.grow([
                    u"    value = helpers.get('%s')\n" % segments[-1],
                    u"    segments = %s\n" % str(segments),
                    u"    scope = '%s'\n" % segments[-2],
                    u"    if scope == '@blog':\n"
                    u"        scope = 'root'\n"
                    u"    if value is None:\n",
                    u"        value = %s\n" % path,
                    u"    if hasattr(value, '__call__'):\n"
                    u"        context_ = resolve(context, '"  + u"', '".join(segments[:-1]) + u"')\n",
                    u"        value = value(context_, scope%s\n" % call,
                ])
            self._result.grow([
                u"    if hasattr(value, '__call__'):\n"
                u"        value = value(context, scope%s\n" % call,
                ])
            if realname:
                self._result.grow(
                    u"    elif value is None:\n"
                    u"        value = helpers['helperMissing'](context, '%s'%s\n"
                        % (realname, call)
                    )

    def add_escaped_expand(self, path_type_path, arguments_):
        if len(arguments_) > 0 and type(arguments_[0]) == tuple:
            (arguments, scope) = arguments_[0]
        else:
            arguments = arguments_
        (path_type, path) = path_type_path
        segments = None
        if path_type is 'complex':
            segments = filter(lambda a: a != '', path)
            path = u"resolve(context, '" + u"', '".join(segments) + u"')"
        call = self.arguments_to_call(arguments)
        self.find_lookup(path, path_type, call, segments=segments)
        if path != "navigation" and path != "pagination":
            self._result.grow([
                u"    result.grow(prepare(value, True))\n"
                ])

    def add_expand(self, path_type_path, arguments):
        (path_type, path) = path_type_path
        call = self.arguments_to_call(arguments)
        self.find_lookup(path, path_type, call)
        self._result.grow([
            u"    result.grow(prepare(value, False))\n"
            ])

    def _debug(self):
        self._result.grow(u"    import pdb;pdb.set_trace()\n")

    def add_invertedblock(self, symbol, arguments, nested, alt_nested):
        # This may need to be a blockHelperMissing clal as well.

        if len(arguments_) > 0 and type(arguments_[0]) is tuple:
            (arguments, scope) = arguments_[0]
        else:
            arguments = arguments_
        name = nested.name
        self._locals[name] = nested

        if alt_nested:
            alt_name = alt_nested.name
            self._locals[alt_name] = alt_nested

        call = self.arguments_to_call(arguments)
        self._result.grow([
            u"    options = {'inverse': %s}\n" % self._wrap_nested(name),
            u"    options['helpers'] = helpers\n"
            u"    options['partials'] = partials\n"
            u"    options['root'] = root\n"
            ])
        if alt_nested:
            self._result.grow([
                u"    options['fn'] = ",
                self._wrap_nested(alt_name),
                u"\n"
                ])
        else:
            self._result.grow([
                u"    options['inverse'] = lambda this: None\n"
                ])
        if symbol == 'foreach' or symbol == 'each':
            if len(arguments_) == 2:
                (key, value) = tuple(arguments_[1].split('='))
                assert key == 'columns'
            else:
                value = "None"
            self._result.grow([
                u"    value = resolve(context, '%s')\n" % scope[0],
                u"    value = helpers['%s'](context, options, value, '%s', columns=%s)\n" % (symbol, scope[0], value),
                u"    result.grow(value or '')\n"
            ])
        else:
            self._result.grow([
                u"    value = helper = helpers.get('%s')\n" % symbol,
                u"    if value is None:\n"
                u"        value = resolve(context, '%s')\n" % symbol,
                u"    if helper and hasattr(helper, '__call__'):\n"
                u"        value = helper(context, options%s\n" % call,
                u"    else:\n"
                u"        value = helpers['blockHelperMissing'](context, options, value, '%s')\n" % symbol,
                u"    result.grow(value or '')\n"
                ])

    def _invoke_template(self, fn_name, this_name):
        self._result.grow([
            u"    result.grow(_partial(%s, %s, helpers=helpers, partials=partials, root=root))\n" % (fn_name, this_name)
        ])


    def add_partial(self, symbol, arguments):
        arg = ""

        if symbol == "navigation" or symbol == "pagination" and not os.path.isfile(_ghostpy_['theme'] + "/partials/" + symbol + ".hbs"):
            path = symbol
        else:
            path = _ghostpy_['theme'] + "/partials/" + symbol + ".hbs"

        overrides = None
        positional_args = 0
        if arguments:
            for argument in arguments:
                kwmatch = re.match('(\w+)=(.+)$', argument)
                if kwmatch:
                    if not overrides:
                        overrides = {}
                    overrides[kwmatch.group(1)] = kwmatch.group(2)
                else:
                    if positional_args != 0:
                        raise PybarsError("An extra positional argument was passed to a partial")
                    positional_args += 1
                    arg = argument

        overrides_literal = 'None'
        if overrides:
            overrides_literal = u'{'
            for key in overrides:
                overrides_literal += u'"%s": %s, ' % (key, overrides[key])
            overrides_literal += u'}'
        self._result.grow([u"    overrides = %s\n" % overrides_literal])
        self._result.grow([u"    path = '%s'\n" % path])
        if symbol == "pagination":
            self._result.grow([
                # u"    import pdb; pdb.set_trace()\n"
                u"    _ghostpy_['scope'] = 'pagination'\n"
                u"    scope_ = Scope(context['pagination'], context, root, overrides=overrides)\n"])
            self._invoke_template("path", "scope_")
            self._result.grow([
                u"    _ghostpy_['scope'] = scope\n"
            ])
        else:
            self._result.grow([
                # u"    import pdb; pdb.set_trace()\n"
                u"    scope_ = Scope(%s, context, root, overrides=overrides)\n" % self._lookup_arg(arg)])
            self._invoke_template("path", "scope_")

class Compiler:

    """A handlebars template compiler.

    The compiler is not threadsafe: you need one per thread because of the
    state in CodeBuilder.
    """

    # _handlebars = OMeta.makeGrammar(handlebars_grammar, {}, 'handlebars')
    # _builder = CodeBuilder()
    # _compiler = OMeta.makeGrammar(compile_grammar, {'builder': _builder})

    def _asset(self, *args, **kwargs):
        return _ghostpy_['theme'] + "/assets/"+args[2]


    def _image(self, *args, **kwargs):
        path = args[0].get('image')
        absolute = False
        if 'absolute' in kwargs.keys():
            absolute = kwargs.get('absolute')
        if absolute:
            return 'http://localhost:63342/pybars3/' + path
        else:
            return path

    def __init__(self, theme):
        self._handlebars = OMeta.makeGrammar(handlebars_grammar, {}, 'handlebars')
        self._builder = CodeBuilder()
        self._compiler = OMeta.makeGrammar(compile_grammar, {'builder': self._builder})
        self._helpers = {}
        self.template_counter = 1
        _ghostpy_['theme'] = theme

    def _generate_code(self, source):
        """
        Common compilation code shared between precompile() and compile()

        :param source:
            The template source as a unicode string

        :return:
            A tuple of (function, source_code)
        """

        if not isinstance(source, str_class):
            raise PybarsError("Template source must be a unicode string")

        tree, error = self._handlebars(source).apply('template')

        self.clean_whitespace(tree)

        if debug:
            print('\nAST')
            print('---')
            print(tree)
            print('')

        if error[1]:
            line_num = source.count('\n') + 1
            beginning_of_line = source.rfind('\n', 0, error[0])
            if beginning_of_line == -1:
                char_num = error[0]
            else:
                char_num = error[0] - beginning_of_line
            if error[1][0][0] == 'message':
                message = error[1][0][1]
            elif error[1][0][0] == 'expected':
                message = 'expected "%s"' % error[1][0][2]
            else:
                message = repr(error[1][0])
            raise PybarsError("Error at character %s of line %s - %s" % (char_num, line_num, message))

        # Ensure the builder is in a clean state - kinda gross
        self._compiler.globals['builder']._reset()

        output = self._compiler(tree).apply('compile')[0]
        return output

    def precompile(self, source):
        """
        Generates python source code that can be saved to a file for caching

        :param source:
            The template to generate source for - should be a unicode string

        :return:
            Python code as a unicode string
        """

        return self._generate_code(source).full_code

    def compile(self, source, path=None):
        """Compile source to a ready to run template.

        :param source:
            The template to compile - should be a unicode string

        :return:
            A template function ready to execute
        """

        _ghostpy_['helpers'].update({"asset": self._asset, "image": self._image})

        container = self._generate_code(source)

        def make_module_name(name, suffix=None):
            output = 'ghostpy._templates.%s' % name
            if suffix:
                output += '_%s' % suffix
            return output

        if not path:
            path = '_template'
            generate_name = True
        else:
            path = path.replace('\\', '/')
            path = path.replace('/', '_')
            mod_name = make_module_name(path)
            if mod_name in sys.modules:
                generate_name = True

        if generate_name:
            mod_name = make_module_name(path, self.template_counter)
            while mod_name in sys.modules:
                self.template_counter += 1
                mod_name = make_module_name(path, self.template_counter)

        mod = ModuleType(mod_name)
        filename = '%s.py' % mod_name.replace('ghostpy.', '').replace('.', '/')
        exec(compile(container.full_code, filename, 'exec', dont_inherit=True), mod.__dict__)
        sys.modules[mod_name] = mod
        linecache.getlines(filename, mod.__dict__)

        return mod.__dict__[container.name]

    def clean_whitespace(self, tree):
        """
        Cleans up whitespace around block open and close tags if they are the
        only thing on the line

        :param tree:
            The AST - will be modified in place
        """

        pointer = 0
        end = len(tree)

        while pointer < end:
            piece = tree[pointer]
            if piece[0] == 'block':
                child_tree = piece[3]

                # Look at open tag, if the only other thing on the line is whitespace
                # then delete it so we don't introduce extra newlines to the output
                open_pre_whitespace = False
                open_pre_content = True
                if pointer > 1 and tree[pointer - 1][0] == 'whitespace' and (tree[pointer - 2][0] == 'newline' or tree[pointer - 2] == 'template'):
                    open_pre_whitespace = True
                    open_pre_content = False
                elif pointer > 0 and (tree[pointer - 1][0] == 'newline' or tree[pointer - 1] == 'template'):
                    open_pre_content = False

                open_post_whitespace = False
                open_post_content = True
                child_len = len(child_tree)
                if child_len > 2 and child_tree[1][0] == 'whitespace' and child_tree[2][0] == 'newline':
                    open_post_whitespace = True
                    open_post_content = False
                elif child_len > 1 and child_tree[1][0] == 'newline':
                    open_post_content = False

                if not open_pre_content and not open_post_content:
                    if open_pre_whitespace:
                        tree.pop(pointer - 1)
                        pointer -= 1
                        end -= 1
                    if open_post_whitespace:
                        child_tree.pop(1)
                    child_tree.pop(1)  # trailing newline

                # Do the same thing, but for the close tag
                close_pre_whitespace = False
                close_pre_content = True
                child_len = len(child_tree)
                if child_len > 2 and child_tree[child_len - 1][0] == 'whitespace' and child_tree[child_len - 2][0] == 'newline':
                    close_pre_whitespace = True
                    close_pre_content = False
                elif child_len > 1 and child_tree[child_len - 1][0] == 'newline':
                    close_pre_content = False

                close_post_whitespace = False
                close_post_content = True
                tree_len = len(tree)
                if tree_len > pointer + 2 and tree[pointer + 1][0] == 'whitespace' and tree[pointer + 2][0] == 'newline':
                    close_post_whitespace = True
                    close_post_content = False
                elif tree_len == pointer + 2 and tree[pointer + 1][0] == 'whitespace':
                    close_post_whitespace = True
                    close_post_content = False
                elif tree_len > pointer + 1 and tree[pointer + 1][0] == 'newline':
                    close_post_content = False
                elif tree_len == pointer + 1:
                    close_post_content = False

                if not close_pre_content and not close_post_content:
                    if close_pre_whitespace:
                        child_tree.pop()
                    child_tree.pop()  # preceeding newline
                    if close_post_whitespace:
                        tree.pop(pointer + 1)
                        end -= 1

                self.clean_whitespace(child_tree)

            pointer += 1

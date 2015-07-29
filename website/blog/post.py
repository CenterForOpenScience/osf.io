from file_handler import FileHandler
from website.models import User
from website.profile.utils import get_gravatar
from website.addons import signals
import subprocess


def parse_blog(posts, node):
    blog = parse_header(posts[1], node)
    prev_ = posts[0]
    next_ = posts[2]
    blog_dict = {
        'title': blog.get('title'),
        'post_class': blog.get('post_class'),
        'date': blog.get('date'),
        'content': _md(blog.get('content')),
        'file': blog.get('file'),
        'author': blog.get('author'),
        'tags': [{
            'id': 'foo',
            'name': 'Foo',
            'description': 'Foo Description',
            'url': 'tags/foo/'},
        {
            'id': 'bar',
            'name': 'Bar',
            'description': 'Bar Description',
            'url': 'tags/bar/'
        }]
    }
    if next_ is not None:
        next = parse_header(next_, node)
        blog_dict['next_post'] =  {
            'title': next.get('title'),
            'content':  _md(next.get('content')),
            'file': next.get('file'),
            'date': next.get('date'),
            'author': next.get('author')
        },
    if prev_ is not None:
        prev = parse_header(prev_, node)
        blog_dict['prev_post'] =  {
            'title': prev.get('title'),
            'content':  _md(prev.get('content')),
            'file': prev.get('file'),
            'date': prev.get('date'),
            'author': prev.get('author')
        }
    return blog_dict

def parse_header(blog_, node):
    file_handler = FileHandler(node)
    blog = file_handler.read_file(blog_)
    blog_dict = {
        'title': '',
        'post_class': '',
        'date': '',
        'file': '',
        'author': ''
    }
    meta = blog[blog.find("/**")+3:blog.find("**/")]
    for line in meta.split("\n"):
        if line != "":
            key, value = line.strip().split(": ")
            blog_dict[key] = value
    content = blog[blog.find("**/")+3:]
    blog_dict['content'] = content
    id = blog_dict['author']
    user = User.load(id)
    try:
        website = user.social['personal']
    except KeyError:
        website = None
    blog_dict['author'] = {
            'id': id,
            'name': user.fullname,
            'bio': 'test bio',
            'url': '/author/1',
            'image': get_gravatar(user, 75),
            'location': 'Location',
            'website': website
        }
    return blog_dict

def parse_posts(posts, guid):
    index = []
    for post in posts:
        post_dict = parse_header(post, guid)
        post_dict['content'] = _md(post_dict['content'])
        index.append(post_dict)
    return index

def _md(content):
    return subprocess.check_output(["/usr/local/bin/node", "website/static/js/pages/blog.js", content])

@signals.blog_change.connect
def _blog_change(*args, **kwargs):
    dict = parse_header(args[0], args[0].node)
    print dict

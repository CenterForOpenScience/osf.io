import markdown2
from file_handler import FileHandler

def parse_blog(posts, guid, user, password):
    blog = parse_header(posts[1], guid, user, password)
    prev_ = posts[0]
    next_ = posts[2]
    blog_dict = {
        'title': blog.get('title'),
        'post_class': blog.get('post_class'),
        'date': blog.get('date'),
        'content': blog.get('content'),
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
        next = parse_header(next_, guid, user, password)
        blog_dict['next_post'] =  {
            'title': next.get('title'),
            'content':  next.get('content'),
            'file': next.get('file'),
            'date': next.get('date'),
            'author': next.get('author')
        },
    if prev_ is not None:
        prev = parse_header(prev_, guid, user, password)
        blog_dict['prev_post'] =  {
            'title': prev.get('title'),
            'content':  prev.get('content'),
            'file': prev.get('file'),
            'date': prev.get('date'),
            'author': prev.get('author')
        }
    return blog_dict

def parse_header(blog_, guid, user, password):
    file_handler = FileHandler(guid, user, password)
    blog = file_handler.read_file(blog_)
    blog_dict = {
        'title': '',
        'post_class': '',
        'date': '',
        'file': ''
    }
    meta = blog[blog.find("/**")+3:blog.find("**/")]
    for line in meta.split("\n"):
        if line != "":
            key, value = line.strip().split(": ")
            blog_dict[key] = value
    content = markdown2.markdown(blog[blog.find("**/")+3:])
    blog_dict['content'] = content
    blog_dict['author'] = {
            'name': 'Jo Bloggs',
            'bio': 'test bio',
            'url': '/author/1',
            'location': 'Location',
            'website': 'http://facebook.com'
        }
    return blog_dict

def parse_posts(posts, guid, user, password):
    index = []
    for post in posts:
        post_dict = parse_header(post, guid, user, password)
        index.append(post_dict)
    return index

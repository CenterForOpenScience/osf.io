import markdown2


def parse_blog(posts):
    blog = parse_header(posts[1])
    prev = parse_header(posts[0])
    next = parse_header(posts[2])
    blog_dict = {
        'title': blog.get('title'),
        'post_class': blog.get('post_class'),
        'date': blog.get('date'),
        'content': blog.get('content'),
        'author': {
            'name': 'Jo Bloggs',
            'bio': 'test bio',
            'url': '/author/1',
            'location': 'Location',
            'website': 'http://facebook.com'
        },
        'url': blog.get('url'),
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
        }],
        'next_post': {
            'title': next.get('title'),
            'excerpt':  next.get('content'),
            'url': next.get('url'),
            'date': next.get('date')
        },
        'prev_post': {
            'title': prev.get('title'),
            'excerpt':  prev.get('content'),
            'url': prev.get('url'),
            'date': prev.get('date')
        }
    }
    return blog_dict

def parse_header(blog):
    blog_dict = {
        'title': '',
        'post_class': '',
        'date': '',
        'url': ''
    }
    meta = blog[blog.find("/**")+3:blog.find("**/")]
    for line in meta.split("\n"):
        if line != "":
            key, value = line.strip().split(": ")
            blog_dict[key] = value
    content = markdown2.markdown(blog[blog.find("**/")+3:])
    blog_dict['content'] = content
    return blog_dict
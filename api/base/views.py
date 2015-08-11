from rest_framework.views import APIView
from rest_framework.response import Response


from .utils import absolute_reverse
from api.users.serializers import UserSerializer


class Root(APIView):
    """
        <p>Welcome to the V2 Open Science Framework API. With this API you can programatically access users,
        projects, components, and files from the <a href="https://osf.io/">Open Science Framework</a>. The Open Science
        Framework is a website that
         integrates with the scientist's daily workflow. OSF helps document and archive study designs, materials, and data.
         OSF facilitates sharing of materials and data within a research group or between groups. OSF also facilitates
         transparency of research and provides a network design that details and credits individual
         contributions for all aspects of the research process.</p>
         <p>NOTE: This API is currently in beta. The beta period should be fairly short, but until then, details about
         the api could change. Once this notice disappears, it will be replaced with a description of how long we will
         support the current api and under what circumstances it might change.</p>
         <h2>General API Usage</h2>
        <p>Each endpoint will have its own documentation, but there are some general things that should work pretty much everywhere.</p>
        <h3>Filtering</h3>
        <p>Collections can be filtered by adding a query parameter in the form:</p>
        <pre>filter[&lt;fieldname&gt;]=&lt;matching information&gt;</pre>
        <p>For example, if you were trying to find <a href="http://en.wikipedia.org/wiki/Lise_Meitner">Lise Meitner</a>:</p>
        <pre>/users?filter[fullname]=meitn</pre>
        <p>You can filter on multiple fields, or the same field in different ways, by &-ing the query parameters together.</p>
        <pre>/users?filter[fullname]=lise&filter[family_name]=mei</pre>
        <h3>Links</h3>
        <p>Responses will generally have associated links. These are helpers to keep you from having to construct
        URLs in your code or by hand. If you know the route to a high-level resource, then feel free to just go to that
        route. For example, going to:</p>
        <pre>/nodes/&lt;node_id&gt;</pre>
        <p>is a perfectly good route to create rather than going to /nodes/ and navigating from there by filtering by id
        (which would be ridiculous). However, if you are creating something that crawls the structure of a node
        going to child node or gathering children, contributors, and similar related resources, then grab the link from
        the object you\'re crawling rather than constructing the link yourself.
        In general, links include:</p>
        <ol>
        <li> "Related" links, which will give you detail information on individual items or a collection of related resources;</li>
        <li> "Self" links, which is what you use for general REST operations (POST, DELETE, and so on);</li>
        <li> Pagination links such as "next", "prev", "first", and "last". These are great for navigating long lists of information.</li></ol>
        <p>Some routes may have extra rules for links, especially if those links work with external services. Collections
        may have counts with them to indicate how many items are in that collection.</p>

    """

    action = 'list'
    def get(self, request, format=None):
        if request.user and not request.user.is_anonymous():
            user = request.user
            current_user = UserSerializer(user, context={'request': request}).data
        else:
            current_user = None
        return Response({
            'meta': {
                'message': 'Welcome to the OSF API.',
                'version': request.version,
                'current_user': current_user,
            },
            'links': {
                'nodes': absolute_reverse('nodes:node-list'),
                'users': absolute_reverse('users:user-list'),
            }
        })

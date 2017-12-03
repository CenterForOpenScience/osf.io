<%inherit file="base.mako"/>

<%def name="title()">OSF Reviews</%def>

<%def name="content()">
<h2>Reviews service is not activated.</h2>
<ul>
<li>Set the following in local.py:</li>
<pre><code>USE_EXTERNAL_EMBER = True
EXTERNAL_EMBER_APPS = {
  'reviews': {
    'url': '/reviews/',
    'server': 'http://localhost:4400',
    'path': '/reviews/'
  }
}</code></pre>
<li>Start the reviews container with <code>docker-compose up -d reviews</code>.</li>
</ul>
</%def>

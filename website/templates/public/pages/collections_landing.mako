<%inherit file="base.mako"/>

<%def name="title()">OSF Collections</%def>

<%def name="content()">
<h2>Collections service is not activated.</h2>
<ul>
<li>Set the following in local.py:</li>
<pre><code>USE_EXTERNAL_EMBER = True
EXTERNAL_EMBER_APPS = {
  'collections': {
    'url': '/collections/',
    'server': 'http://localhost:4204',
    'path': '/collections/'
  }
}</code></pre>
<li>Start the collections container with <code>docker-compose up -d collections</code>.</li>
</ul>
</%def>

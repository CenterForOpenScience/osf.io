<%inherit file="base.mako"/>

<%def name="title()">Quickfiles</%def>

<%def name="content()">
<h2>Quickfiles service is not activated.</h2>
<ul>
<li>Set the following in local.py:</li>
<pre><code>USE_EXTERNAL_EMBER = True
EXTERNAL_EMBER_APPS = {
  'quickfiles': {
    'url': '/quickfiles/',
    'server': 'http://localhost:4201',
    'path': '/quickfiles/'
  }
}</code></pre>
<li>Start the quickfiles container with <code>docker-compose up -d quickfiles</code>.</li>
</ul>
</%def>

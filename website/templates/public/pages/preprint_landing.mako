<%inherit file="base.mako"/>

<%def name="title()">Preprints</%def>

<%def name="content()">
<h2>Preprints service is not activated.</h2>
<ul>
<li>Set the following in local.py:</li>
<pre><code>USE_EXTERNAL_EMBER = True
EXTERNAL_EMBER_APPS = {
  'preprints': {
    'url': '/preprints/',
    'server': 'http://localhost:4200',
    'path': '/preprints/'
  }
}</code></pre>
<li>Start the preprints container with <code>docker-compose up -d preprints</code>.</li>
</ul>
</%def>

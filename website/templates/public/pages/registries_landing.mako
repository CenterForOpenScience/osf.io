<%inherit file="base.mako"/>

<%def name="title()">Registries</%def>

<%def name="content()">
<h2>Registries service is not activated.</h2>
<ul>
<li>Set the following in local.py:</li>
<pre><code>USE_EXTERNAL_WEB_APP = True
EXTERNAL_WEB_APPS = {
  'registries': {
    'url': '/registries/',
    'server': 'http://localhost:4300',
    'path': '/registries/'
  }
}</code></pre>
<li>Start the registries container with <code>docker-compose up -d registries</code>.</li>
</ul>
</%def>

<%inherit file="project/addon/widget.mako"/>
<%page expression_filter="h"/>

<div id="markdown-it-render">${wiki_content | n}</div>

<% import json %>
<script>
    window.contextVars = $.extend(true, {}, window.contextVars, {
        usePythonRender: ${json.dumps(use_python_render)},
        urls: {
            wikiContent: '${wiki_content_url}'
        }
    })
</script>
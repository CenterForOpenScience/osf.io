<%inherit file="project/addon/widget.mako"/>
<%page expression_filter="h"/>

<div id="markdownRender">
    % if wiki_content:
        ${wiki_content | n}
    % else:
        <p><em>No wiki content</em></p>
    % endif
</div>

<% import json %>
<script>
    window.contextVars = $.extend(true, {}, window.contextVars, {
        wikiWidget: true,
        usePythonRender: ${json.dumps(use_python_render)},
        urls: {
            wikiContent: '${wiki_content_url}'
        }
    })
</script>

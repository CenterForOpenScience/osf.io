<%inherit file="project/addon/widget.mako"/>
<%page expression_filter="h"/>

<div id="markdownRender" class="break-word">
    % if wiki_content:
        ${wiki_content | n}
    % else:
        <p><em>No wiki content</em></p>
    % endif
</div>

<div id="more_link">
    % if more:
        <a href="${node['url']}${short_name}/">Read More</a>
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

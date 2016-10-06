<%inherit file="project/addon/widget.mako"/>

<div id="markdownRender" class="break-word scripted">
    % if wiki_content:
        ${wiki_content}
    % else:
        <p><em>No wiki content</em></p>
    % endif
</div>

<div id="more_link">
    % if more:
        <a href="${node['url']}${short_name}/">Read More</a>
    % endif
</div>

<script>
    window.contextVars = $.extend(true, {}, window.contextVars, {
        wikiWidget: true,
        renderedBeforeUpdate: ${ rendered_before_update | sjson, n },
        urls: {
            wikiContent: ${wiki_content_url | sjson, n }
        }
    })
</script>

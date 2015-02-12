<%inherit file="project/addon/widget.mako"/>
<%page expression_filter="h"/>

<div id="markdown-it-render"></div>

<script>
    window.contextVars = $.extend(true, {}, window.contextVars, {
        urls: {
            wikiContent: '${wiki_content_url}'
        }
    })
</script>
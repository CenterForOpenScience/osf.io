<%inherit file="project/addon/widget.mako" />
<script type="text/javascript">
window.contextVars = $.extend(true, {}, window.contextVars, {
    zotero: {
        folder_id: '${list_id | js_str}'
    }
});
</script>
<div class="citation-picker">
    <input id="citationStyleSelect" type="hidden" />
</div>
<div id="zoteroWidget" class="citation-widget">
</div>

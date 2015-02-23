<%inherit file="project/addon/widget.mako" />
<script type="text/javascript">
window.contextVars = $.extend(true, {}, window.contextVars, {
    zotero: {
        folder_id: '${list_id | js_str}'
    }
});
</script>
<link rel="stylesheet" href="/static/addons/zotero/citations_widget.css">
<div class="citation-picker" style="padding-bottom: 6px;">
    <input id="zoteroStyleSelect" type="hidden" />
</div>
<div id="zoteroWidget" class="citation-widget">
</div>

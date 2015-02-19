<%inherit file="project/addon/widget.mako" />
<script type="text/javascript">
window.contextVars = $.extend(true, {}, window.contextVars, {
    mendeley: {
        folder_id: '${list_id | js_str}'
    }
});
</script>
<link rel="stylesheet" href="/static/addons/mendeley/citations_widget.css">
<input id="mendeleyStyleSelect" type="hidden" />
<div id="mendeleyWidget">
</div>

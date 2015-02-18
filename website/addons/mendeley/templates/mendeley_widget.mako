<%inherit file="project/addon/widget.mako" />
<script type="text/javascript">
window.contextVars = $.extend(true, {}, window.contextVars, {
    mendeley: {
        folder_id: '${list_id | js_str}'
    }
 });
</script>
<input id="mendeleyStyleSelect" type="hidden" />
<div id="mendeleyWidget">
    <ul data-bind="foreach: citations">
        <li data-bind="text: $data"></li>
    </ul>
</div>

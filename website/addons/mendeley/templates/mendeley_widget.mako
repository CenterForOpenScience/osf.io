<%inherit file="project/addon/widget.mako" />
<input id="mendeleyStyleSelect" type="hidden" />
<div id="mendeleyWidget">
    <ul data-bind="foreach: citations">
        <li data-bind="text: $data"></li>
    </ul>
</div>

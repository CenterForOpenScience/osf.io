<%inherit file="project/addon/widget.mako" />
<div id="zoteroWidget">
    <ul data-bind="foreach: citations">
        <li data-bind="text: $data"></li>
    </ul>
</div>
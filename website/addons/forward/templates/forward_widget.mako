<%inherit file="project/addon/widget.mako" />

<div id="forwardScope" class="scripted">

    <div id="forwardModal" class="p-lg" style="display: none;">

        <div>
            This project contains a forward to
            <a data-bind="attr: {href: url}, text: url"></a>.
        </div>

        <div class="spaced-buttons m-t-md" data-bind="visible: redirecting">
            <a class="btn btn-default" data-bind="click: cancelRedirect">Cancel</a>
            <a class="btn btn-primary" data-bind="click: doRedirect">Redirect</a>
        </div>

    </div>

    <div id="forwardWidget" data-bind="visible: url() !== null">

        <div>
            This project contains a forward to
            <a data-bind="attr: {href: url}, text: linkDisplay" target="_blank"></a>.
        </div>

        <div class="spaced-buttons m-t-sm">
            <a class="btn btn-primary" data-bind="click: doRedirect">Redirect</a>
        </div>

    </div>

</div>

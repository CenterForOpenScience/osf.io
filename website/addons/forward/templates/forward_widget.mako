<%inherit file="project/addon/widget.mako" />

<div id="forwardScope" class="scripted">

    <div id="forwardModal" style="display: none; padding: 15px;">

        <div>
            This project contains a forward to
            <a data-bind="attr.href: url">{{ url }}</a>.
        </div>

        <p>You will be automatically forwarded in {{ timeLeft }} seconds.</p>

        <div class="spaced-buttons" data-bind="visible: redirecting">
            <a class="btn btn-success" data-bind="click: doRedirect">Redirect</a>
            <a class="btn btn-warning" data-bind="click: cancelRedirect">Cancel</a>
        </div>

    </div>

    <div id="forwardWidget" data-bind="visible: url() !== null">

        <div>
            This project contains a forward to
            <a data-bind="attr.href: url" target="_blank">{{ linkDisplay }}</a>.
        </div>

        <div class="spaced-buttons">
            <a class="btn btn-success" data-bind="click: doRedirect">Redirect</a>
        </div>

    </div>

</div>

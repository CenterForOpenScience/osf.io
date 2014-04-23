<div id="forwardScope" class="scripted">

    <h4 class="addon-title">
        Forward
    </h4>

    <!-- Settings Pane -->
    <div class="forward-settings">

        <form class="form" data-bind="submit: submitSettings">

            <div class="form-group">
                <label for="forwardUrl">Forward URL</label>
                <input
                        id="forwardUrl"
                        class="form-control"
                        data-bind="value: url"
                    />
            </div>

            <div class="form-group">
                <label for="forwardBool">Automatic Forward</label>
                <select class="form-control" data-bind="
                        options: boolOptions,
                        optionsText: getBoolLabel,
                        value: redirectBool
                    "></select>
            </div>

            <div class="form-group">
                <label for="forwardSecs">Forward Delay</label>
                <input
                        id="forwardSecs"
                        class="form-control"
                        data-bind="value: redirectSecs"
                        type="number"
                    />
            </div>

            <div class="pull-right">
                <input
                        type="submit"
                        class="btn btn-primary"
                        value="Submit"
                        data-bind="disable: !validators.isValid()"
                    />
            </div>

        </form>

        <!-- Flashed Messages -->
        <div class="help-block">
            <p data-bind="html: message, attr.class: messageClass"></p>
        </div>

    </div><!-- end .forward-settings -->

</div><!-- end #forwardScope -->

<script>
    $script(['/static/addons/forward/forwardConfig.js']);
    $script.ready('forwardConfig', function() {
        var url = '${node['api_url'] + 'forward/config/'}';
        var forward = new ForwardConfig('#forwardScope', url);
    });
</script>

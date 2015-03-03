<div id="forwardScope" class="scripted">

    <h4 class="addon-title">
        External Link
    </h4>

    <!-- Settings Pane -->
    <div class="forward-settings">

        <form class="form" data-bind="submit: submitSettings">

            <div class="form-group">
                <label for="forwardUrl">URL</label>
                <input
                        id="forwardUrl"
                        class="form-control"
                        data-bind="value: url"
                    />
            </div>
	    
            <div class="form-group">
                    <label for="forwardLabel">Label</label>
                    <input
                            id="forwardLabel"
                            class="form-control"
                            data-bind="value: label"
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
                        data-bind="value: redirectSecs, enable: redirectBool"
                        type="number"
                    />
            </div>

            <div class="row">
                <div class="col-md-10 overflow">
                    <p data-bind="html: message, attr.class: messageClass"></p>
                </div>
                <div class="col-md-2">
                    <input type="submit"
                           class="btn btn-primary pull-right"
                           value="Submit"
                           data-bind="disable: !validators.isValid()"
                    />
                </div>
            </div>

        </form>

    </div><!-- end .forward-settings -->

</div><!-- end #forwardScope -->


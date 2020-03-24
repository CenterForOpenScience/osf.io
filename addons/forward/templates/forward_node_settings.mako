<div id="forwardScope" class="scripted">

    <!-- Settings Pane -->
    <div class="forward-settings">

        <form class="form" data-bind="submit: submitSettings">

            <div class="form-group">
                <label for="forwardUrl">URL</label>
                <input
                        id="forwardUrl"
                        class="form-control"
                        data-bind="value: url"
                        placeholder="${_('Send people who visit your GakuNin RDM project page to this link instead')}"
                        />
            </div>

            <div class="form-group">
                    <label for="forwardLabel">${ _("Label")}</label>
                    <input
                            id="forwardLabel"
                            class="form-control"
                            data-bind="value: label"
                            placeholder="${_('Optional')}"
                        />
                </div>


            <div class="row">
                <div class="col-md-10 overflow">
                    <p data-bind="html: message, attr: {class: messageClass}"></p>
                </div>
                <div class="col-md-2">
                    <input type="submit"
                           class="btn btn-success pull-right"
                           value="${_('Save')}"
                    />
                </div>
            </div>

        </form>

    </div><!-- end .forward-settings -->

</div><!-- end #forwardScope -->


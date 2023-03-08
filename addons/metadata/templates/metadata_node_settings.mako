<!-- for widget -->

<div id="${addon_short_name}Scope" class="scripted">
    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        ${addon_full_name}
    </h4>
    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings">
        <div data-bind="if: incompletedAddonSettings().length === 0" class="row">
            <div class="col-md-12">
                ${_("No configuration items.")}
            </div>
        </div>
        <div data-bind="if: applicableAddonSettings().length > 0" class="row">
            <div class="col-md-12">
                ${_("Imported add-on settings can be restored:")}
                <span data-bind="foreach: applicableAddonSettings">
                    <!-- ko if: $index() > 0 -->,<!-- /ko -->
                    <span data-bind="text: full_name" style="font-weight: bold;"></span>
                </span>
            </div>
            <div class="col-md-12">
                <button href="#metadataApplyDialog" data-toggle="modal"
                        class="btn btn-primary">
                    ${_("Apply")}
                </button>
            </div>
        </div>
        <div data-bind="if: nonApplicableAddonSettings().length > 0" class="row text-warning">
            <div class="col-md-12">
                ${_("Please set the credentials for each add-on to apply the imported add-on settings:")}
                <span data-bind="foreach: nonApplicableAddonSettings">
                    <!-- ko if: $index() > 0 -->,<!-- /ko -->
                    <span data-bind="text: full_name" style="font-weight: bold;"></span>
                </span>
            </div>
        </div>
        <!-- end row -->
    </div>

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>

    <!-- Confirm dialog -->
    <div id="metadataApplyDialog" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h3>${_("Apply imported add-on settings")}</h3>
            </div>

            <form>
                <div class="modal-body">

                    <div class="row">

                        <div class="col-sm-12">

                            <p>
                                ${_("Restore imported add-on settings? This operation performs settings for folders, etc., using the imported settings.")}
                            </p>

                        </div>

                    </div><!-- end row -->

                </div><!-- end modal-body -->

                <div class="modal-footer">

                    <a href="#" class="btn btn-default" data-dismiss="modal">${_("Cancel")}</a>
                    <button data-bind="click: applyAddonSettings" class="btn btn-success">${_("OK")}</button>

                </div><!-- end modal-footer -->

            </form>

        </div><!-- end modal-content -->
    </div>
</div>

</div>

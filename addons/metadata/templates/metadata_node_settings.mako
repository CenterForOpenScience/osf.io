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
                <!-- ko if: applicableAddonSettings().length === 1 -->
                    ${_("Please set the credential for the %(addonName)s add-on to access the storage\
                    attatched to the import source.")  % dict(
                        addonName='<span data-bind="text: applicableAddonSettings()[0].full_name" style="font-weight: bold;"></span>'
                    ) | n}
                <!-- /ko -->
                <!-- ko if: applicableAddonSettings().length > 1 -->
                    ${_("To access the storages attatched to the import source, please set the credentials for each add-on: ")}
                    <span data-bind="foreach: applicableAddonSettings">
                        <!-- ko if: $index() > 0 -->,<!-- /ko -->
                        <span data-bind="text: full_name" style="font-weight: bold;"></span>
                    </span>
                <!-- /ko -->
            </div>
            <div class="col-md-12" style="margin-bottom: 1em;">
                <button href="#metadataApplyDialog" data-toggle="modal"
                        class="btn btn-primary">
                    ${_("Restore Add-ons")}
                </button>
            </div>
        </div>
        <div data-bind="if: nonApplicableAddonSettings().length > 0" class="row text-warning">
            <div class="col-md-12">
                <!-- ko if: nonApplicableAddonSettings().length === 1 -->
                    ${_("Please set the credential for the %(addonName)s add-on to access the storage\
                    attatched to the import source.")  % dict(
                        addonName='<span data-bind="text: nonApplicableAddonSettings()[0].full_name" style="font-weight: bold;"></span>'
                    ) | n}
                <!-- /ko -->
                <!-- ko if: nonApplicableAddonSettings().length > 1 -->
                    ${_("To access the storages attatched to the import source, please set the credentials for each add-on: ")}
                    <span data-bind="foreach: nonApplicableAddonSettings">
                        <!-- ko if: $index() > 0 -->,<!-- /ko -->
                        <span data-bind="text: full_name" style="font-weight: bold;"></span>
                    </span>
                <!-- /ko -->
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
                <h3>${_("Restore imported add-on settings")}</h3>
            </div>

            <form>
                <div class="modal-body">

                    <div class="row">

                        <div class="col-sm-12">

                            <p>
                                ${_("Apply the add-on settings from the import source.\
                                This will make the storage attatched to the original project available.")}
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

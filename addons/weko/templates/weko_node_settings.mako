<div id="${addon_short_name}Scope" class="scripted">

    <!-- Add credentials modal -->
    <%include file="weko_credentials_modal.mako"/>

    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        ${addon_full_name}

        <small class="authorized-by">
            <span data-bind="if: nodeHasAuth">
                authorized by <a data-bind="attr: {href: urls().owner}, text: ownerName"></a>
                % if not is_registration:
                    <a data-bind="click: deauthorize"
                        class="text-danger pull-right addon-auth">Disconnect Account</a>
                % endif
            </span>

             <!-- Import Access Token Button -->
            <span data-bind="if: showImport">
                <a data-bind="click: importAuth" href="#" class="text-primary pull-right addon-auth">
                    Import Account from Profile
                </a>
            </span>

            <!-- Oauth Start Button -->
            <span data-bind="if: showTokenCreateButton">
                <a href="#wekoInputCredentials" data-toggle="modal" class="pull-right text-primary addon-auth">
                    Connect  Account
                </a>
            </span>

        </small>
    </h4>

    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings" data-bind="visible: showSettings">
        <div class="row">
            <div class="col-md-12">

                <!-- The linked index -->
                <p>
                    <strong>Current Index:</strong>
                    <span data-bind="ifnot: submitting">
                        <span data-bind="if: showLinkedIndex">
                            <a data-bind="attr: {href: savedIndexUrl()}, text: savedIndexTitle"></a>
                        </span>
                        <span data-bind="ifnot: showLinkedIndex" class="text-muted">
                            None
                        </span>
                    </span>
                    <span data-bind="if: submitting">
                        <i class="fa fa-spinner fa-lg fa-spin"></i>
                    </span>
                </p>

                <div data-bind="if: userIsOwner">
                    <span data-bind="if: hasIndices">
                        <div class="row">

                            <!--  Picker -->
                            <div class="col-md-6">
                                Index:
                                <select class="form-control"
                                        data-bind="options: indices,
                                                   optionsValue: 'id',
                                                   optionsText: 'title',
                                                   value: selectedIndexId">
                                </select>
                            </div>
                        </div>
                    </span>

                    <span class="text-info" data-bind="ifnot: hasIndices">
                         There are no indices associated with the connected account.
                   </span>

                <!-- Save button for set info -->
                    <span data-bind="if: showSubmitIndex">
                        <br>
                        <button data-bind="enable: enableSubmitIndex, click: setInfo"
                                class="btn btn-success pull-right">
                            Save
                        </button>
                    </span>
                </div>
            </div>
            <!-- end col -->
        </div>
        <!-- end row -->
    </div>
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
</div>

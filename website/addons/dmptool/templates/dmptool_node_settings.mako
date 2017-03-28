<div id="${addon_short_name}Scope" class="scripted">

    <!-- Add credentials modal -->
    <%include file="dmptool_credentials_modal.mako"/>

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
                <a href="#dmptoolInputCredentials" data-toggle="modal" class="pull-right text-primary addon-auth">
                    Connect  Account
                </a>
            </span>

        </small>
    </h4>

    <%doc>
    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings" data-bind="visible: showSettings">
        <div class="row">
            <div class="col-md-12">

                <!-- The linked dmptool Host -->
                <p class="break-word">
                    <strong>dmptool Repository:</strong>
                    <a data-bind="attr: {href: savedHostUrl()}, text: savedHost"></a>
                </p>

                <!-- The linked dataset -->
                <p>
                    <strong>Current Dataset:</strong>
                    <span data-bind="ifnot: submitting">
                        <span data-bind="if: showLinkedDataset">
                            <a data-bind="attr: {href: savedDatasetUrl()}, text: savedDatasetTitle"></a> on
                            <a data-bind="attr: {href: saveddmptoolUrl()}, text: saveddmptoolTitle || '' + dmptool"></a>.
                        </span>
                        <span data-bind="ifnot: showLinkedDataset" class="text-muted">
                            None
                        </span>
                    </span>
                    <span data-bind="if: submitting">
                        <i class="fa fa-spinner fa-lg fa-spin"></i>
                    </span>
                </p>

                <div data-bind="if: showNotFound" class="text-danger">
                    The current dataset was not found on dmptool.
                </div>

                <div data-bind="if: userIsOwner">
                    <span data-bind="if: hasdmptools">
                        <div class="row">

                            <!-- dmptool Picker -->
                            <div class="col-md-6">
                                dmptool:
                                <select class="form-control"
                                        data-bind="options: dmptools,
                                                   optionsValue: 'alias',
                                                   optionsText: 'title',
                                                   value: selecteddmptoolAlias,
                                                   event: {change: getDatasets}">
                                </select>
                            </div>

                            <!-- Dataset Picker -->
                            <div class="col-md-6">
                                Dataset:
                                <div data-bind="if: showDatasetSelect">
                                    <select class="form-control"
                                            data-bind="options: datasets,
                                                       optionsValue: 'doi',
                                                       optionsText: 'title',
                                                       value: selectedDatasetDoi">
                                    </select>
                                </div>
                                <div data-bind="if: showNoDatasets">
                                    <div class="text-info" style="padding-top: 8px">
                                        No datasets available.
                                    </div>
                                </div>
                                <div data-bind="ifnot: loadedDatasets">
                                    <i class="fa fa-spinner fa-lg fa-spin"
                                       style="padding-bottom: 8px; padding-top: 8px"></i>
                                    <span class="text-info">Retrieving datasets...</span>
                                </div>
                            </div>
                        </div>
                    </span>

                    <span class="text-info" data-bind="ifnot: hasdmptools">
                         There are no dmptools, datasets, or files associated with the connected account.
                   </span>

                <!-- Save button for set info -->
                    <span data-bind="if: showSubmitDataset">
                        <br>
                        <button data-bind="enable: enableSubmitDataset, click: setInfo"
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

    </%doc>

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
</div>

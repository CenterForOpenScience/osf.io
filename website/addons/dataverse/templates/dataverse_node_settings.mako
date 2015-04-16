<div id="dataverseScope" class="scripted">

    <h4 class="addon-title">
        Dataverse
        <small class="authorized-by">

            <span data-bind="if: nodeHasAuth">
                    authorized by <a data-bind="attr.href: urls().owner">
                        {{ownerName}}
                    </a>
                    % if not is_registration:
                        <a data-bind="click: clickDeauth"
                            class="text-danger pull-right addon-auth">Deauthorize</a>
                    % endif
            </span>

            <span data-bind="if: showLinkDataverse">
                <a data-bind="click: importAuth" class="text-primary pull-right addon-auth">
                    Import API Token
                </a>
            </span>

        </small>

    </h4>

    <div class="dataverse-settings" data-bind="if: nodeHasAuth && connected">

        <!-- The linked dataset -->
        <p>
            <strong>Current Dataset:</strong>
            <span data-bind="ifnot: submitting">
                <span data-bind="if: showLinkedDataset">
                    <a data-bind="attr.href: savedDatasetUrl()"> {{ savedDatasetTitle }}</a> on
                    <a data-bind="attr.href: savedDataverseUrl()"> {{ savedDataverseTitle }} Dataverse</a>.
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
            The current dataset was not found on Dataverse.
        </div>

        <div data-bind="if: userIsOwner">
            <span data-bind="if: hasDataverses">
                <div class="row">
                    <div class="col-md-6">
                        Dataverse:
                        <select class="form-control"
                                data-bind="options: dataverses,
                                           optionsValue: 'alias',
                                           optionsText: 'title',
                                           value: selectedDataverseAlias,
                                           event: {change: getDatasets}">
                        </select>
                    </div>

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

            <div class="text-info" data-bind="ifnot: hasDataverses">
                The Dataverse user associated with this node does not currently have any published Dataverses.
            </div>

        </div>

    </div>

    <!-- Changed Credentials -->
    <div class="text-info dataverse-settings" data-bind="if: credentialsChanged">
        <span data-bind="if: userIsOwner">
            Your dataverse credentials may not be valid. Please re-enter your api token.
        </span>
        <span data-bind="ifnot: userIsOwner">
            There was a problem connecting to the Dataverse with the given
            credentials.
        </span>
    </div>

    <!-- Input Credentials-->
    <form data-bind="if: showInputCredentials">
        <div class="form-group">
            <label for="apiToken">
                API Token
                <a href="{{urls().apiToken}}"
                   target="_blank" class="text-muted addon-external-link">
                    (Get from Dataverse <i class="fa fa-external-link-square"></i>)
                </a>
            </label>
            <input class="form-control" name="apiToken" data-bind="value: apiToken"/>
        </div>
        <!-- Submit button for input credentials -->
        <button data-bind="click: sendAuth" class="btn btn-success">
            Submit
        </button>
    </form>

    <!-- Flashed Messages -->
    <div class="help-block">

    </div>

    <!-- Submit button for set info -->
    <div>
        <div class="row">
            <div class="col-md-10">
                <p data-bind="html: message, attr: {class: messageClass}"></p>
            </div>
            <div class="col-md-2" data-bind="if: showSubmitDataset">
                <button data-bind="enable: enableSubmitDataset, click: setInfo"
                        class="btn btn-primary pull-right">
                    Submit
                </button>
            </div>
        </div>
    </div>
</div>

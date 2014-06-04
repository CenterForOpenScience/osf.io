

<div id="dataverseScope" class="scripted">

    <h4 class="addon-title">
        Dataverse
        <span data-bind="if: nodeHasAuth">
            <small class="authorized-by">
                authorized by <a data-bind="attr.href: urls().owner">
                    {{ownerName}}
                </a>
                <a data-bind="click: clickDeauth"
                    class="text-danger pull-right">Deauthorize</a>
            </small>
        </span>
    </h4>

    <div class="dataverse-settings" data-bind="if: nodeHasAuth && connected">

        <!-- The linked study -->
        <p>
            <strong>Current Study:</strong>
            <span data-bind="if: showLinkedStudy">
                This node is linked to
                <a data-bind="attr.href: savedStudyUrl()"> {{ savedStudyTitle }}</a> on
                <a data-bind="attr.href: savedDataverseUrl()"> {{ savedDataverseTitle }}</a>.
            </span>
            <span data-bind="ifnot: showLinkedStudy">
                None
            </span>
        </p>

        <div data-bind="if: userIsOwner">
            <div class="row" data-bind="if: hasDataverses">
                <div class="col-md-6">
                    Dataverse:
                    <select class="form-control"
                            data-bind="options: dataverses,
                                       optionsValue: 'alias',
                                       optionsText: 'title',
                                       value: selectedDataverseAlias,
                                       event: {change: getStudies}">
                    </select>
                </div>

                <div class="col-md-6">
                    Study:
                    <div data-bind="if: showStudySelect">
                        <select class="form-control"
                                data-bind="options: studies,
                                           optionsValue: 'hdl',
                                           optionsText: 'title',
                                           value: selectedStudyHdl">
                        </select>
                    </div>
                    <div data-bind="if: showNoStudies">
                        <div class="text-info" style="padding-top: 8px">
                            No studies available.
                        </div>
                    </div>
                    <div data-bind="ifnot: loadedStudies">
                        <i class="icon-spinner icon-large icon-spin"
                           style="padding-bottom: 8px; padding-top: 8px"></i>
                        <span class="text-info">Retrieving studies...</span>
                    </div>
                </div>

            </div>

            <div data-bind="if: hasDataverses">
                <div class="padded">
                    <button data-bind="enable: dataverseHasStudies, click: setInfo" class="btn btn-primary pull-right">
                            Submit
                    </button>
                </div>
            </div>

            <div class="text-info" data-bind="ifnot: hasDataverses">
                Dataverse user {{ dataverseUsername }} does not currently have any released Dataverses.
            </div>

        </div>

    </div>

    <div class="dataverse-settings" data-bind="if: credentialsChanged">
        <span data-bind="if: userIsOwner">
            There was a problem connecting to the Dataverse using your
            credentials. If they have changed, please go to
            <a href="/settings/addons/">user settings</a> and update your account
            information.
        </span>
        <span data-bind="ifnot: userIsOwner">
            There was a problem connecting to the Dataverse with the given
            credentials.
        </span>
    </div>

    <!-- Link Dataverse Button -->
    <div data-bind="if: showLinkDataverse">
        <a data-bind="click: importAuth" class="btn btn-primary">
            Authorize: Link to Dataverse Account
        </a>
    </div>

    <!-- Create Dataverse Button -->
    <div data-bind="if: showCreateButton">
        <a data-bind="attr.href: '/settings/addons/'" class="btn btn-primary">
            Authorize: Set Dataverse Account
        </a>
    </div>

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>

</div>

<script>
    $script(['/static/addons/dataverse/dataverseNodeConfig.js'], function() {
        // Endpoint for Dataverse user settings
        var url = '${node["api_url"] + "dataverse/config/"}';
        // Start up the DataverseConfig manager
        var dataverse = new DataverseNodeConfig('#dataverseScope', url);
    });
</script>
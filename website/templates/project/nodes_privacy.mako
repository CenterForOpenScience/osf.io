<div id="nodesPrivacy" class="modal fade" div style="display: none;">
    <div class="modal-dialog modal-md">
        <div style="display: none;" data-bind="visible: true">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" data-bind="click: clear" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                <h3 class="modal-title" data-bind="text:pageTitle"></h3>
            </div>

            <div class="modal-body">

                <!-- warning page -->

                <div data-bind="if: page() == 'warning'">
                    <span data-bind="html:message"></span>
                </div>

                <!-- end warning page -->

                <div data-bind='visible:page() === "select"'>
                    <div class="row">
                        <div class="col-md-10">
                            <div class="m-b-md box p-sm">
                                <span data-bind="html:message"></span>
                            </div>
                        </div>
                    </div>
                    <div>
                        Select:&nbsp;
                        <a data-bind="click:selectAll">Make all public</a>
                        &nbsp;|&nbsp;
                        <a data-bind="click:selectNone">Make all private</a>
                    </div>
                        <div class="tb-row-titles">
                            <div style="width: 100%" data-tb-th-col="0" class="tb-th">
                                <span class="m-r-sm"></span>
                            </div>
                        </div>
                        <div class="osf-treebeard">
                            <div id="grid">
                                <div class="spinner-loading-wrapper">
                                    <div class="logo-spin logo-md"></div>
                                    <p class="m-t-sm fg-load-message"> Loading projects and components...  </p>
                                </div>
                            </div>
                            <div class="help-block" style="padding-left: 15px">
                                <p id="configureNotificationsMessage"></p>
                            </div>
                        </div>
                </div>
                <!-- end select projects page -->

                <!-- addon and projects changed warning page -->

                <div data-bind="if: page() == 'addon'">

                    <div class="m-b-md box p-xs" data-bind="visible: changedAddons().length > 0">
                        <span class="text-bigger" data-bind="html:message()['addons']"></span>
                        <ul data-bind="foreach: { data: changedAddons, as: 'item' }">
                            <li>
                                <h4 class="f-w-lg" data-bind="text: item"></h4>
                            </li>
                        </ul>
                        <hr>
                    </div>
                    <div class="m-b-md box p-xs" data-bind="visible: nodesChangedPublic().length > 0">
                        <span class="text-bigger" data-bind="html:message()['nodesPublic']"></span>
                        <ul data-bind="foreach: { data: nodesChangedPublic, as: 'item' }">
                            <li>
                                <h4 class="f-w-lg" data-bind="text: item"></h4>
                            </li>
                        </ul>
                        <hr>
                    </div>
                    <div class="m-b-md box p-xs" data-bind="visible: nodesChangedPrivate().length > 0">
                        <span class="text-bigger" data-bind="html:message()['nodesPrivate']"></span>
                        <ul data-bind="foreach: { data: nodesChangedPrivate, as: 'item' }">
                            <li>
                                <h4 class="f-w-lg" data-bind="text: item"></h4>
                            </li>
                        </ul>
                        <hr>
                    </div>
                    <!-- end addon and projects changed warning page -->

                </div>
            </div><!-- end modal-body -->

            <div class="modal-footer">

                <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">Cancel</a>

                <span data-bind="if: page() == 'warning'">
                    <a class="btn btn-primary" data-bind="click:selectProjects">Next</a>
                </span>

                <span data-bind="if: page() == 'select'">
                    <a class="btn btn-primary" data-bind="click:addonWarning">Next</a>
                </span>

                <span data-bind="if: page() == 'addon'">
                    <a href="#" class="btn btn-primary" data-bind="click: confirmChanges" data-dismiss="modal">Confirm</a>
                </span>

            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
            </div>
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<link href="/static/css/nodes-privacy.css" rel="stylesheet">

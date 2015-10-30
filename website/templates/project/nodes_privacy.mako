<div id="nodesPrivacy" class="modal fade">
    <div class="modal-dialog modal-md">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                <h3 class="modal-title" data-bind="text:pageTitle"></h3>
            </div>

            <div class="modal-body">

                <div data-bind="if: page() == 'warning'">
                    <span data-bind="text:message"></span>
                </div>
                <div data-bind="if: page() == 'addon'">


                    <span data-bind="visible: changedAddons().length > 0">The following addons will be changed:</span>
                    <div>
                        <ul data-bind="foreach: { data: changedAddons, as: 'item' }">
                            <li>
                                <span data-bind="text: item"></span>
                            </li>
                        </ul>
                    </div>
                    <div>
                    <span data-bind="visible: nodesChangedPublic().length > 0">The following nodes will be make public:</span>
                    <ul data-bind="foreach: { data: nodesChangedPublic, as: 'item' }">
                        <li>
                            <span data-bind="text: item"></span>
                        </li>
                    </ul>
                    </div>
                    <div>

                    <span data-bind="visible: nodesChangedPrivate().length > 0">The following nodes will be make private:</span>
                    <ul data-bind="foreach: { data: nodesChangedPrivate, as: 'item' }">
                        <li>
                            <span data-bind="text: item"></span>
                        </li>
                    </ul>
                    </div>
                    <span>Are you sure you would like to continue?</span>


                </div>
                <!-- Invite user page -->

                <div data-bind='visible:page() === "select"'>
                    <div class="row">
                        <div class="col-md-10">
                            <div class="m-b-md box p-sm">
                                <span data-bind="text:message"></span>
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
                                    <div class="logo-spin logo-lg"></div>
                                    <p class="m-t-sm fg-load-message"> Loading projects and components...  </p>
                                </div>
                            </div>
                            <div class="help-block" style="padding-left: 15px">
                                <p id="configureNotificationsMessage"></p>
                            </div>
                        </div>
                </div><!-- end invite user page -->

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
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<link href="/static/css/nodes-privacy.css" rel="stylesheet">

<%def name="javascript()">
    <% import website %>
    ${parent.javascript()}
    <script type="text/javascript">
        window.contextVars = $.extend({}, window.contextVars, {'mailingList': ${website.settings.MAILCHIMP_GENERAL_LIST | sjson, n }});
    </script>
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="${"/static/public/js/notifications-config-page.js" | webpack_asset}"></script>
</%def>

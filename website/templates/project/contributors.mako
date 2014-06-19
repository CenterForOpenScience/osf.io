<%inherit file="project/project_base.mako"/>
<%def name="title()">Contributors</%def>

<div class="row">
    <div class="col-md-12">

        <h2>Contributors</h2>
            % if 'admin' in user['permissions']:
                <div class="text-align">Drag and drop contributors to change listing order.</div>
            % endif
            <div id="manageContributors" class="scripted">
                    <table id="manageContributorsTable" class="table">
                        <thead>
                            <tr>
                            <th class="col-sm-6">Name</th>
                            <th class="col-sm-3">
                                <i class="icon-question-sign permission-info"
                                        data-toggle="popover"
                                        data-title="Permission Information"
                                        data-container="body"
                                        data-placement="left"
                                        data-html="true"
                                    ></i>
                                Permissions
                            </th>
                            <th class="col-sm-1">
                                <i class="icon-question-sign visibility-info"
                                        data-toggle="popover"
                                        data-title="Visibility Information"
                                        data-container="body"
                                        data-placement="left"
                                        data-html="true"
                                    ></i>
                                Visibility
                            </th>
                            <th class="col-sm-1 col-offset-1"></th>
                            </tr>
                        </thead>
                        <tr data-bind="if: canEdit">
                            <td colspan="3">
                                <a href="#addContributors" data-toggle="modal">
                                    Add a contributor
                                </a>
                            </td>
                        </tr>
                        <tbody data-bind="sortable: {
                                template: 'contribTpl',
                                data: contributors,
                                as: 'contributor',
                                isEnabled: canEdit,
                                afterRender: setupEditable,
                                options: {
                                    containment: '#manageContributors'
                                }
                            }">
                        </tbody>
                    </table>
                    ${buttonGroup()}
            </div>


    % if 'admin' in user['permissions']:
        <h2>Sharing</h2>
        <div class="text-align">Create a link to share this project so those who have the link can view but not edit the project</div>
        <div class="scripted" id="linkScope">

            <table id="privateLinkTable" class="table">

                <thead>
                    <tr>
                    <th class="col-sm-3">Link</th>
                    <th class="col-sm-4">What This Link Shares</th>
                    <th class="col-sm-2">Created Date</th>
                    <th class="col-sm-2">Created By</th>
                    <th class="col-sm-1"></th>
                    </tr>
                </thead>

                <tbody>

                    <tr>
                        <td colspan="3">
                            <a href="#addPrivateLink" data-toggle="modal">
                                Create a link
                            </a>
                        </td>
                    </tr>

                </tbody>
                <tbody data-bind="foreach: {data: privateLinks, afterRender: updateClipboard}">
                        <tr>
                        <td class="col-sm-3">
                            <span data-bind="text: name, tooltip: {title: linkName}"></span>

                                <div class="btn-group">
                                <button class="btn btn-default btn-mini copy-button" data-trigger="manual" rel="tooltip" title="Click to copy the link"
                                        data-bind="attr: {data-clipboard-text: linkUrl}" >
                                    <span class="icon-copy" ></span>
                                </button>
                                    <input class="link-url" type="text" data-bind="value: linkUrl, attr:{readonly: readonly}"  />
                                </div>

                        </td>
                        <td class="col-sm-4" >

                               <ul class="narrow-list list-overflow" data-bind="foreach:nodesList">
                                   <li data-bind="style:{marginLeft: $data.scale}">
                                      <img data-bind="attr:{src: imgUrl}" /><a data-bind="text:$data.title, attr: {href: $data.url}"></a>
                                   </li>
                               </ul>
                               <button class="btn btn-default btn-mini more-link-node" data-bind="text:hasMoreText, visible: moreNode, click: displayAllNodes"></button>
                               <button class="btn btn-default btn-mini more-link-node" data-bind="text:collapse, visible:collapseNode, click: displayTwoNodes"></button>
                        </td>

                        <td class="col-sm-2">
                            <span class="link-create-date" data-bind="text: dateCreated.local, tooltip: {title: dateCreated.utc}"></span>
                        </td>
                        <td class="col-sm-2" data-bind="text: creator"></td>
                        <td class="col-sm-1">
                            <a class="remove-private-link btn btn-danger btn-mini" rel="tooltip" title="Remove this link" data-bind="click: $root.removeLink">–</a>
                        </td>
                        </tr>
                </tbody>

            </table>

        </div>
    % endif

    </div><!-- end col-md -->
</div><!-- end row -->


<script id="contribTpl" type="text/html">
    <tr data-bind="click: unremove, css: {'contributor-delete-staged': deleteStaged}">
        <td>
            <img data-bind="attr: {src: contributor.gravatar_url}" />
            <span data-bind="text: contributor.fullname"></span>
        </td>
        <td>
            <!-- ko if: $parent.canEdit -->
                <span data-bind="visible: notDeleteStaged">
                    <a href="#" class="permission-editable" data-type="select"></a>
                </span>
                <span data-bind="visible: deleteStaged">
                    <span data-bind="text: formatPermission"></span>
                </span>
            <!-- /ko -->
            <!-- ko ifnot: $parent.canEdit -->
                <span data-bind="text: formatPermission"></span>
            <!-- /ko -->
        </td>
        <td>
            <input
                    type="checkbox"
                    data-bind="checked: visible, enable: $parent.canEdit"
                />
        </td>
        <td>
            <!-- ko if: $parent.canEdit -->
                <!-- ko ifnot: deleteStaged -->
                    <a
                            class="btn btn-danger contrib-button btn-mini"
                            data-bind="click: remove"
                            rel="tooltip"
                            title="Remove contributor"
                        >–</a>
                <!-- /ko -->
                <!-- ko if: deleteStaged -->
                    Removed
                <!-- /ko -->
            <!-- /ko -->

            <!-- ko ifnot: $parent.canEdit -->
                <!-- ko if: canRemove -->
                    <a
                            class="btn btn-danger contrib-button btn-mini"
                            data-bind="click: removeSelf"
                            rel="tooltip"
                            title="Remove contributor"
                        >-</a>
                    <!-- /ko -->
            <!-- /ko -->
        </td>
    </tr>
</script>


<%def name="buttonGroup()">
    % if 'admin' in user['permissions']:
        <a class="btn btn-danger contrib-button" data-bind="click: cancel, visible: changed">Discard Changes</a>
        <a class="btn btn-success contrib-button" data-bind="click: submit, visible: canSubmit">Save Changes</a>
        <br /><br />
        <div data-bind="foreach: messages">
            <div data-bind="css: cssClass">{{ text }}</div>
        </div>
    % endif
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <% import json %>

    <script type="text/javascript">
    $script(['/static/js/contribManager.js'], function() {
        var contributors = ${json.dumps(contributors)};
        var user = ${json.dumps(user)};
        var isRegistration = ${json.dumps(node['is_registration'])};
        manager = new ContribManager('#manageContributors', contributors, user, isRegistration);
    });

    $script(['/static/js/privateLinkManager.js',
             '/static/js/privateLinkTable.js']);

    $script.ready(['privateLinkManager', 'privateLinkTable'], function () {
        // Controls the modal
        var configUrl = nodeApiUrl + 'get_editable_children/';
        var privateLinkManager = new PrivateLinkManager('#addPrivateLink', configUrl);

        var tableUrl = nodeApiUrl + 'private_link/';
        var privateLinkTable = new PrivateLinkTable('#linkScope', tableUrl);
    });

    $("body").on('click', ".link-url", function(e) { e.target.select() });

    </script>
</%def>

<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Contributors</%def>

<%include file="project/modal_generate_private_link.mako"/>
<%include file="project/modal_add_contributor.mako"/>

<div class="row">
    <div class="col-md-12">

        <h2>Contributors</h2>
            % if 'admin' in user['permissions']:
                <p>Drag and drop contributors to change listing order.</p>
            % endif
            <div id="manageContributors" class="scripted">
            <!-- ko if: canEdit -->
            <a href="#addContributors" data-toggle="modal" class="btn btn-primary">
                Add Contributors
            </a>
            <!-- /ko -->
                <table id="manageContributorsTable" class="table">
                    <thead>
                        <tr>
                        <th class="col-md-6">Name</th>
                        <th class="col-md-2">
                            Permissions
                            <i class="icon-question-sign permission-info"
                                    data-toggle="popover"
                                    data-title="Permission Information"
                                    data-container="body"
                                    data-placement="right"
                                    data-html="true"
                                ></i>
                        </th>
                        <th class="col-md-3">
                            Visibility
                            <i class="icon-question-sign visibility-info"
                                    data-toggle="popover"
                                    data-title="Visibility Information"
                                    data-container="body"
                                    data-placement="right"
                                    data-html="true"
                                ></i>
                        </th>
                        <th class="col-md-1">
                        </th>
                        </tr>
                    </thead>
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
        <h2>View-only Links</h2>
        <div class="text-align">Create a link to share this project so those who have the link can view&mdash;but not edit&mdash;the project</div>
        <div class="scripted" id="linkScope">

            <table id="privateLinkTable" class="table">

                <thead>
                    <tr>
                    <th class="col-sm-3">Link</th>
                    <th class="col-sm-4">What This Link Shares</th>

                    <th class="col-sm-2">Created Date</th>
                    <th class="col-sm-2">Created By</th>
                    <th class="col-sm-1">Anonymous</th>
                    <th class="col-sm-0"></th>
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
                <tbody data-bind="foreach: {data: privateLinks, afterRender: afterRenderLink}">
                    <tr>
                        <td class="col-sm-3">
                            <div>
                                <span class="link-name overflow-block" data-bind="text: name, tooltip: {title: linkName}" style="width: 200px"></span>
                            </div>
                            <div class="btn-group">
                            <button class="btn btn-default btn-mini copy-button" data-trigger="manual" rel="tooltip" title="Click to copy the link"
                                    data-bind="attr: {data-clipboard-text: linkUrl}" >
                                <span class="icon-copy" ></span>
                            </button>
                                <input class="link-url" type="text" data-bind="value: linkUrl, attr:{readonly: readonly}"  />
                            </div>
                        </td>
                        <td class="col-sm-4">
                           <ul class="narrow-list list-overflow" data-bind="foreach: nodesList">
                               <li data-bind="style:{marginLeft: $data.scale}">
                                  <img data-bind="attr:{src: imgUrl}" /><a data-bind="text:$data.title, attr: {href: $data.url}"></a>
                               </li>
                           </ul>
                           <button class="btn btn-default btn-mini more-link-node" data-bind="text:hasMoreText, visible: moreNode, click: displayAllNodes"></button>
                           <button class="btn btn-default btn-mini more-link-node" data-bind="text:collapse, visible:collapseNode, click: displayDefaultNodes"></button>
                        </td>

                        <td class="col-sm-2">
                            <span class="link-create-date" data-bind="text: dateCreated.local, tooltip: {title: dateCreated.utc}"></span>
                        </td>
                        <td class="col-sm-2" >
                            <a data-bind="text: creator.fullname, attr: {href: creator.url}" class="overflow-block" style="width: 300px"></a>
                        </td>
                        <td class="col-sm-1">
                            <span data-bind="text: anonymousDisplay"></span>
                        </td>
                        <td class="col-sm-0">
                            <a data-bind="click: $root.removeLink, tooltip: {title: removeLink}">
                                <i class="icon-remove text-danger"></i>
                            </a>
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
            <span data-bind="ifnot: profileUrl">
                <span data-bind="text: contributor.shortname"></span>
            </span>
            <span data-bind="if: profileUrl">
                <a class="no-sort" data-bind="text: contributor.shortname, attr:{href: profileUrl}"></a>
            </span>
        </td>
        <td>
            <!-- ko if: $parent.canEdit -->
                <span data-bind="visible: notDeleteStaged">
                    <a href="#" class="permission-editable no-sort" data-type="select"></a>
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
                    type="checkbox" class="no-sort"
                    data-bind="checked: visible, enable: $parent.canEdit"
                />
        </td>
        <td>
            <!-- ko if: $parent.canEdit -->
                <!-- ko ifnot: deleteStaged -->
                    <!-- Note: Prevent clickBubble so that removing a
                     contributor does not immediately un-remove her. -->
                    <a
                            data-bind="click: remove, clickBubble: false, tooltip: {title: removeContributor}"
                        >
                                <i class="icon-remove text-danger no-sort"></i>
                    </a>
                <!-- /ko -->
                <!-- ko if: deleteStaged -->
                    Removed
                <!-- /ko -->
            <!-- /ko -->

            <!-- ko ifnot: $parent.canEdit -->
                <!-- ko if: canRemove -->
                    <a
                            data-bind="click: removeSelf"
                            rel="tooltip"
                            title="Remove contributor"
                        >
                        <i class="icon-remove text-danger no-sort"></i>
                    </a>
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
      window.contextVars = window.contextVars || {};
      window.contextVars.user = ${json.dumps(user)};
      window.contextVars.isRegistration = ${json.dumps(node['is_registration'])};
      window.contextVars.contributors = ${json.dumps(contributors)};

    </script>
    <script src="/static/public/js/sharing-page.js"></script>

</%def>

<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Contributors</%def>

<%include file="project/modal_generate_private_link.mako"/>
<%include file="project/modal_add_contributor.mako"/>

<div class="page-header  visible-xs">
  <h2 class="text-300">Contributors</h2>
</div>

<div class="col-md-3 col-xs-12">
    <div class="filters">
        <input type="text" class="form-control searchable" id="nameSearch" placeholder="Search by name"/>
        <h5>Permissions:</h5>
        <div class="btn-group btn-group-justified-vertical filtergroup" id='permissionFilter'>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id="admins">Administrator</button>
            </div>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id="write">Read + Write</button>
            </div>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id="read">Read</button>
            </div>
        </div>
        <h5>Cited:</h5>
        <div class="btn-group btn-group-justified-vertical filtergroup" id='citedFilter'>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id='cited'>Cited</button>
            </div>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id='notCited'>Not Cited</button>
            </div>
        </div>
    </div>
</div>

<div class="col-md-9 col-xs-12">
    <div id="manageContributors" class="scripted">
        <h3> Contributors
            <!-- ko if: canEdit -->
                <a href="#addContributors" data-toggle="modal" class="btn btn-success btn-sm" style="margin-left:20px;margin-top: -3px">
                  <i class="fa fa-plus"></i> Add
                </a>
            <!-- /ko -->
        </h3>
        % if 'admin' in user['permissions'] and not node['is_registration']:
            <p>Drag and drop contributors to change listing order.</p>
        % endif


    <table  id="manageContributorsTable"
            class="table responsive-table responsive-table-xxs"
            data-bind="template: {
                name: 'contribTable',
                afterRender: afterRender,
                options: {
                    containment: '#manageContributors'
                },
                data: 'contrib'
                }">
    </table>
    <span id="adminContributorsAnchor" class="project-page anchor"></span>
    <div id="adminContributors" data-bind="if: adminContributors.length">
        <h4>
            Admins on Parent Projects
            <i class="fa fa-question-circle admin-info"
                  data-content="These users are not contributors on
                  this component but can view and register it because they
                    are administrators on a parent project."
                  data-toggle="popover"
                  data-title="Admins on Parent Projects"
                  data-container="body"
                  data-placement="right"
                  data-html="true"
            ></i>
        </h4>
        <table  id="adminContributorsTable"
                class="table responsive-table responsive-table-xxs"
                data-bind="template: {
                    name: 'contribTable',
                    afterRender: afterRender,
                    options: {
                        containment: '#manageContributors'
                    },
                    data: 'admin'
                }">
        </table>
    </div>
        ${buttonGroup()}
    </div>

    % if 'admin' in user['permissions']:
        <h3>View-only Links
            <a href="#addPrivateLink" data-toggle="modal" class="btn btn-success btn-sm" style="margin-left:20px;margin-top: -3px">
              <i class="fa fa-plus"></i> Add
            </a>
        </h3>
        <p>Create a link to share this project so those who have the link can view&mdash;but not edit&mdash;the project.</p>
        <div class="scripted" id="linkScope">
            <table id="privateLinkTable" class="table responsive-table responsive-table-xs">
                <thead>
                    <tr>
                        <th class="responsive-table-hide">Link Name</th>
                        <th style="width: 120px;">Shared Components</th>
                        <th>Created Date</th>
                        <th>Created By</th>
                        <th style="width: 78px">Anonymous</th>
                        <th style="width: 78px"></th>
                    </tr>
                </thead>
                <tbody data-bind="template: {
                            name: 'linkTbl'
                        }">
                </tbody>
            </table>
        </div>
    % endif
</div>

<link rel="stylesheet" href="/static/css/pages/contributor-page.css">

<script id="linkTbl" type="text/html">
    <!-- ko foreach: privateLinks -->
    <tr>
        <td>
            <span class="link-name m-b-xs" data-bind="text: name" style="display: inline-block;"></span>
            <span class="fa fa-angle-down toggle-icon"></span>
            <div>
                <div class="btn-group" style="width: 100% display: flex; display: -webkit-flex; display: -ms-flex;">
                    <button title="Copy to clipboard" class="btn btn-default btn-sm m-r-xs copy-button"
                            data-bind="attr: {data-clipboard-text: linkUrl}" >
                        <i class="fa fa-copy"></i>
                    </button>
                    <input style='width: 100%' class="table-only link-url" type="text" data-bind="value: linkUrl, attr:{readonly: readonly}"  />
                    <input style='width: 75%' class="card-subheader link-url" type="text" data-bind="value: linkUrl, attr:{readonly: readonly}"  />
                </div>
            </div>
        </td>

        <td>
            <div class="td-content">
                <ul class="private-link-list narrow-list" data-bind="foreach: nodesList">
                    <li data-bind="style:{marginLeft: $data.scale}">
                        <span data-bind="getIcon: $data.category"></span>
                        <a data-bind="text:$data.title, attr: {href: $data.url}"></a>
                    </li>
                </ul>
            </div>
        </td>
        <td>
            <div class="td-content">
                <span class="link-create-date" data-bind="text: dateCreated.local, tooltip: {title: dateCreated.utc}"></span>
            </div>
        </td>
        <td>
            <div class="td-content">
                <a data-bind="text: creator.fullname, attr: {href: creator.url}" class="overflow-block" style="width: 300px"></a>
            </div>
        </td>
        <td>
            <div class="td-content">
                <span data-bind="html: anonymousDisplay"></span>
                <!-- ko if: $root.nodeIsPublic && anonymous -->
                <i data-bind="tooltip: {title: 'Public projects are not anonymized.'}" class="fa fa-question-circle fa-sm"></i>
                <!-- /ko -->
            </div>
        </td>
        <td>
            <div class="td-content">
                <button data-bind="click:  $root.removeLink" type="button" class="btn btn-danger to-top-element">Remove</button>
            </div>
        </td>
    </tr>
    <!-- /ko -->
</script>

<script id="contribTable" type="text/html">
    <thead>
        <tr>
            <th class="responsive-table-hide" style="width: 40px">Name</th>
            <th style="min-width: 140px"></th>
            <th style="min-width: 127px">
                Permissions
                <i class="fa fa-question-circle permission-info"
                    data-toggle="popover"
                    data-title="Permission Information"
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i>
            </th>
            <th style="width: 109px">
                Bibliographic Contributor
                <i class="fa fa-question-circle visibility-info"
                    data-toggle="popover"
                    data-title="Bibliographic Contributor Information"
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i>
            </th>
            <th style="width: 78px"></th>
        </tr>
    </thead>
    <!-- ko if: $data == 'contrib' -->
    <tbody id="contributors" data-bind="template: {
            name: 'contribRow',
            foreach: $root.contributors,
            as: 'contributor',
            afterMove: $root.afterMove
    }"></tbody>
    <!-- /ko -->
    <!--ko if: $data == 'admin' -->
        <tbody data-bind="template: {
            name: 'contribRow',
            foreach: $root.adminContributors,
            as: 'contributor',
        }">
    </tbody>
    <!-- /ko -->
</script>

<script id="contribRow" type="text/html">
    <tr class="items" data-bind="click: unremove, css: {'contributor-delete-staged': $parent.deleteStaged}">
        <td>
            <img data-bind="attr: {src: contributor.gravatar_url}" />
            <span class="fa fa-angle-down toggle-icon"></span>
            <div class="card-header">
                <span style="display: block" data-bind="ifnot: profileUrl">
                    <span class="name-search" data-bind="text: contributor.shortname"></span>
                </span>
                <span style="display: block" data-bind="if: profileUrl">
                    <a onclick="cancelProp(event)" class="no-sort name-search" data-bind="text: contributor.shortname, attr:{href: profileUrl}"></a>
                </span>
                <span style="display: block" data-bind="text: permissionText()" class="permission-filter permission-search"></span>
            </div>
        </td>
        <td class="table-only">
            <span data-bind="ifnot: profileUrl">
                <span class="name-search" data-bind="text: contributor.shortname"></span>
            </span>
            <span data-bind="if: profileUrl">
                <a class="no-sort name-search" data-bind="text: contributor.shortname, attr:{href: profileUrl}"></a>
            </span>
        </td>
        <td class="permissions">
            <div class="td-content">
                <!-- ko if: contributor.canEdit() -->
                    <span data-bind="visible: notDeleteStaged">
                        <select class="form-control input-sm" data-bind="
                            options: $parents[1].permissionList,
                            value: permission,
                            optionsText: function(val) {
                                return $parents[1].permissionDict[val];
                                },
                             style: { font-weight: permissionChange() ? 'normal' : 'bold' }"
                        >
                        </select>
                    </span>
                    <span data-bind="visible: deleteStaged">
                        <span data-bind="text: permissionText()"></span>
                    </span>
                <!-- /ko -->
                <!-- ko ifnot: contributor.canEdit() -->
                    <span data-bind="text: permissionText()"></span>
                <!-- /ko -->
            </div>
        </td>
        <td>
            <div class="td-content">
                <input
                    type="checkbox" class="no-sort biblio cited-filter"
                    data-bind="checked: visible, enable: $data.canEdit() && !contributor.isAdmin"
                />
            </div>
        </td>
        <td>
            <div class="td-content">
                <!-- ko if: contributor.canEdit() -->
                    <!-- ko ifnot: deleteStaged -->
                        <!-- Note: Prevent clickBubble so that removing a
                        contributor does not immediately un-remove her. -->
                            <button type="button" class="btn btn-danger" data-bind="click: remove, clickBubble: false">Remove</button>
                    <!-- /ko -->
                    <!-- ko if: deleteStaged -->
                        Save to Remove
                    <!-- /ko -->
                <!-- /ko -->

                <!-- ko ifnot: contributor.canEdit() -->
                    <!-- ko if: canRemove -->
                        <button type="button" class="btn btn-danger" data-bind="click: function() { $data.removeSelf($parents[1])}">Remove2</button>
                    <!-- /ko -->
                <!-- /ko -->
            </div>
        </td>
    </tr>
</script>

<%def name="buttonGroup()">
    % if 'admin' in user['permissions']:
        <a class="btn btn-danger contrib-button" data-bind="click: cancel, visible: changed">Discard Changes</a>
        <a class="btn btn-success contrib-button" data-bind="click: submit, visible: canSubmit">Save Changes</a>
        <br /><br />
    % endif
        <div data-bind="foreach: messages">
            <div data-bind="css: cssClass">{{ text }}</div>
        </div>
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}

    <script type="text/javascript">
      window.contextVars = window.contextVars || {};
      window.contextVars.user = ${ user | sjson, n };
      window.contextVars.isRegistration = ${ node['is_registration'] | sjson, n };
      window.contextVars.contributors = ${ contributors | sjson, n };
      window.contextVars.adminContributors = ${ adminContributors | sjson, n };
    </script>

    <script src=${"/static/public/js/sharing-page.js" | webpack_asset}></script>

</%def>

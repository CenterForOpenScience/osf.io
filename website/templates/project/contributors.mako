<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} ${_("Contributors")}</%def>

<%include file="project/modal_add_contributor.mako"/>
<%include file="project/modal_remove_contributor.mako"/>

<div class="page-header  visible-xs">
  <h2 class="text-300">${_("Contributors")}</h2>
</div>

<div class="col-md-3 col-xs-12">
    <div class="filters">
        <input type="text" class="form-control searchable" id="nameSearch" placeholder="${_('Filter by name')}"/>
        <h5 class="m-t-md">${_("Permissions")}
                <i class="fa fa-question-circle permission-info"
                    data-toggle="popover"
                    data-title="${_('Permission Information')}"
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i></h5>
        <div class="btn-group btn-group-justified-vertical filtergroup" id='permissionFilter'>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id="admins">${_("Administrator")}</button>
            </div>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id="write">${_("Read + Write")}</button>
            </div>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id="read">${_("Read")}</button>
            </div>
        </div>
        <h5 class="m-t-md">${_("Bibliographic Contributor")}
                <i class="fa fa-question-circle visibility-info"
                    data-toggle="popover"
                    data-title=${_('Bibliographic Contributor Information')}
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i></h5>
        <div class="btn-group btn-group-justified-vertical filtergroup" id='visibleFilter'>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id='visible'>${_("Bibliographic")}</button>
            </div>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id='notVisible'>${_("Non-Bibliographic")}</button>
            </div>
        </div>
    </div>
</div>

<div class="col-md-9 col-xs-12">
    <div id="manageContributors" class="scripted">
        <h3> ${_("Contributors")}
            <!-- ko if: canEdit -->
                <a href="#addContributors" data-toggle="modal" class="btn btn-success btn-sm m-l-md">
                  <i class="fa fa-plus"></i> ${_("Add")}
                </a>
            <!-- /ko -->
        </h3>

        % if permissions.ADMIN in user['permissions'] and not node['is_registration']:
            <p class="m-b-xs">${_("Drag and drop contributors to change listing order.")}</p>
        % endif

    <div data-bind="filters: {
            items: ['.contrib', '.admin'],
            toggleClass: 'btn-default btn-primary',
            manualRemove: true,
            groups: {
                permissionFilter: {
                    filter: '.permission-filter',
                    type: 'text',
                    buttons: {
                        admins: '${_("Administrator")}',
                        write: '${_("Read + Write")}',
                        read: '${_("Read")}'
                    }
                },
                visibleFilter: {
                    filter: '.visible-filter',
                    type: 'checkbox',
                    buttons: {
                        visible: true,
                        notVisible: false
                    }
                }
            },
            inputs: {
                nameSearch: '.name-search'
            }
        }">
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
    </div>
    <div data-bind="visible: $root.empty" class="no-items text-danger m-b-md">
        ${_("No contributors found")}
    </div>
    <span id="adminContributorsAnchor" class="project-page anchor"></span>
    <div id="adminContributors" data-bind="if: adminContributors().length">
        <h4>
            ${_("Admins on Parent Projects")}
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
        <div id="noAdminContribs" data-bind="visible: $root.adminEmpty" class="text-danger no-items m-b-md">
            ${_("No administrators from parent project found.")}
        </div>
    </div>
        ${buttonGroup()}
    </div>

    % if permissions.ADMIN in user['permissions'] and access_requests and node['access_requests_enabled']:
    <div id="manageAccessRequests">
        <h3> ${_("Requests for Access")}</h3>
        <p class="m-b-xs">${_("The following users have requested access to this project.")}</p>
        <table  id="manageAccessRequestsTable"
        class="table responsive-table responsive-table-xxs"
        data-bind="template: {
            name: 'accessRequestsTable',
            afterRender: afterRender,
            options: {
                containment: '#manageAccessRequests'
            }
            }">
        </table>
    </div>
    % endif

    % if permissions.ADMIN in user['permissions']:
      % if not use_viewonlylinks:
        <div style="display: none;">
      % endif
        <h3 class="m-t-xl">${_("View-only Links")}
            <a href="#addPrivateLink" data-toggle="modal" class="btn btn-success btn-sm m-l-md">
              <i class="fa fa-plus"></i> ${_("Add")}
            </a>
        </h3>
        <p>${_("Create a link to share this project so those who have the link can view&mdash;but not edit&mdash;the project.") | n}</p>
        <%include file="project/private_links.mako"/>
      % if not use_viewonlylinks:
        </div>
      % endif
    % endif
</div>

<link rel="stylesheet" href="/static/css/pages/contributor-page.css">
<link rel="stylesheet" href="/static/css/responsive-tables.css">

<script id="contribTable" type="text/html">
    <thead>
        <tr>
            <th class="responsive-table-hide"
                data-bind="css: {sortable: ($data === 'contrib' && $root.isSortable())}" style="min-width: 100px;white-space: nowrap;">${_("Name")}
            </th>
            <th style="min-width: 140px;width: 200px;white-space: nowrap;"></th>
            <th style="min-width: 150px;width: 160px;white-space: nowrap;">
                ${_("Permissions")}
                <i class="fa fa-question-circle permission-info"
                    data-toggle="popover"
                    data-title="${_('Permission Information')}"
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i>
            </th>
            <th class="biblio-contrib" style="min-width:144px;white-space: nowrap;">
                ${_("Bibliographic Contributor")}
                <i class="fa fa-question-circle visibility-info"
                    data-toggle="popover"
                    data-title="${_('Bibliographic Contributor Information')}"
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i>
            </th>
            <th style="width: 50px;max-width: 100px; white-space: nowrap;"></th>
            <th class="remove"></th>
        </tr>
    </thead>
    <!-- ko if: $data == 'contrib' -->
    <tbody id="contributors" data-bind="sortable: {
            template: 'contribRow',
            data: $root.contributors,
            as: 'contributor',
            isEnabled: $root.isSortable
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

<script id="accessRequestsTable" type="text/html">
    <thead>
        <tr>
            <th class="responsive-table-hide">${_("Name")}</th>
            <th></th>
            <th class="access-permissions">
                ${_("Permissions")}
                <i class="fa fa-question-circle permission-info"
                    data-toggle="popover"
                    data-title="${_('Permission Information')}"
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i>
            </th>
            <th class="biblio-contrib">
                ${_("Bibliographic Contributor")}
                <i class="fa fa-question-circle visibility-info"
                    data-toggle="popover"
                    data-title="${_('Bibliographic Contributor Information')}"
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i>
            </th>
            <th></th>
        </tr>
    </thead>
    <tbody data-bind="template: {
        name: 'accessRequestRow',
        foreach: $root.accessRequests,
        as: 'accessRequest',
    }">
</script>

<script id="contribRow" type="text/html">
    <tr data-bind="visible: !contributor.filtered(), click: unremove, css: {'contributor-delete-staged': $parent.deleteStaged}, attr: {class: $parent}">
        <td data-bind="attr: {class: contributor.expanded() ? 'expanded' : null,
                                role: $root.collapsed() ? 'button' : null},
                       click: $root.collapsed() ? toggleExpand : null">
            <!-- ko if: ($parent === 'contrib' && $root.isSortable()) -->
                <span class="fa fa-bars sortable-bars"></span>
                <img class="m-l-xs" data-bind="attr: {src: contributor.profile_image_url}" />
            <!-- /ko -->
            <!-- ko ifnot: ($parent === 'contrib' && $root.isSortable()) -->
                <img data-bind="attr: {src: contributor.profile_image_url}" />
            <!-- /ko -->
            <span data-bind="attr: {class: contributor.expanded() ? 'fa toggle-icon fa-angle-up' : 'fa toggle-icon fa-angle-down'}"></span>
            <div class="card-header">
                <span data-bind="ifnot: profileUrl">
                    <span class="name-search" data-bind="text: contributor.shortname"></span>
                </span>
                <span data-bind="if: profileUrl">
                    <a class="name-search" data-bind="text: contributor.shortname, attr:{href: profileUrl}"></a>
                </span>
                <span data-bind="text: permissionText()" class="permission-filter permission-search"></span>
            </div>
        </td>
        <td class="table-only">
            <span data-bind="ifnot: profileUrl">
                <span class="name-search" data-bind="text: contributor.shortname"></span>
            </span>
            <span data-bind="if: profileUrl">
                <a class="name-search" data-bind="text: contributor.shortname, attr:{href: profileUrl}"></a>
            </span>
        </td>
        <td class="permissions">
            <div class="header" data-bind="visible: contributor.expanded() && $root.collapsed()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || contributor.expanded()">
                <!-- ko if: contributor.canEdit() -->
                    <span data-bind="visible: !deleteStaged()">
                        <select class="form-control input-sm" data-bind="
                            options: $parents[1].permissionList,
                            value: permission,
                            optionsText: optionsText.bind(permission),
                             style: { 'font-weight': permissionChange() ? 'normal' : 'bold' }"
                        >
                        </select>
                    </span>
                    <span data-bind="visible: deleteStaged">
                        <span data-bind="text: permissionText()"></span>
                    </span>
                    </span>
                <!-- /ko -->
                <!-- ko ifnot: contributor.canEdit() -->
                    <span data-bind="text: permissionText()"></span>
                <!-- /ko -->
            </div>
        </td>
        <td>
            <div class="header" data-bind="visible: contributor.expanded() && $root.collapsed()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || contributor.expanded()">
                <input
                    type="checkbox" class="biblio visible-filter"
                    data-bind="checked: visible, enable: $data.canEdit() && !contributor.isParentAdmin && !deleteStaged()"
                />
            </div>
        </td>
        <td>
            <!-- ko if: (!contributor.registered) -->
            <div class="td-content">
                <a class="btn btn-success btn-sm m-l-md" data-bind="click: reInvite, class: {}">
                    ${_("Invitation Code")}
                </a>
            </div>
            <!-- /ko -->
        </td>
        <td data-bind="css: {'add-remove': !$root.collapsed()}">
            <div class="td-content" data-bind="visible: !$root.collapsed() || contributor.expanded()">
                <!-- ko if: (contributor.canEdit() || canRemove) -->
                        <span href="#removeContributor"
                           data-bind="click: remove, class: {}, visible: !$root.collapsed()"
                           data-toggle="modal"><i class="fa fa-times fa-2x remove-or-reject"></i></span>
                        <button href="#removeContributor" class="btn btn-default btn-sm m-l-md"
                           data-bind="click: remove, visible: $root.collapsed()"
                           data-toggle="modal"><i class="fa fa-times"></i> ${_("Remove")}</button>
                <!-- /ko -->
                <!-- ko if: (canAddAdminContrib) -->
                        <button class="btn btn-success btn-sm m-l-md"
                           data-bind="click: addParentAdmin"
                        ><i class="fa fa-plus"></i> ${_("Add")}</button>
                <!-- /ko -->
            </div>
        </td>
    </tr>
</script>

<script id="accessRequestRow" type="text/html">
    <tr>
        <td data-bind="attr: {class: accessRequest.expanded() ? 'expanded' : null,
                       role: $root.collapsed() ? 'button' : null},
                       click: $root.collapsed() ? toggleExpand : null">
            <span class="fa fa-fw">&nbsp;</span>
            <img data-bind="attr: {src: accessRequest.user.profile_image_url}" />
            <span data-bind="attr: {class: accessRequest.expanded() ? 'fa toggle-icon fa-angle-up' : 'fa toggle-icon fa-angle-down'}"></span>
            <div class="card-header">
                <a data-bind="text: accessRequest.user.shortname, attr:{href: profileUrl}"></a>
                <span data-bind="text: accessRequest.permissionText()"></span>
            </div>
        </td>
        <td class="table-only">
            <a data-bind="text: accessRequest.user.shortname, attr:{href: accessRequest.profileUrl}"></a>
        </td>
        <td class="permissions">
            <div class="header" data-bind="visible: accessRequest.expanded() && $root.collapsed()"></div>
                <div class="td-content" data-bind="visible: !$root.collapsed() ||  accessRequest.expanded()">
                <select class="form-control input-sm" data-bind="
                    options: $parents[0].permissionList,
                    value: permission,
                    optionsText: optionsText.bind(permission)"
                >
                </select>
                <span data-bind="text: permissionText()"></span>
            </div>
        </td>
        <td>
            <div class="header" data-bind="visible: accessRequest.expanded()  && $root.collapsed()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || accessRequest.expanded()">
                <input
                    type="checkbox" class="biblio"
                    data-bind="checked: visible"
                />
            </div>
        </td>
        <td data-bind="css: {'add-remove': !$root.collapsed()}">
            <div class="td-content" data-bind="visible: !$root.collapsed() || accessRequest.expanded()">
                <button class="btn btn-success btn-sm m-l-md request-accept-button"
                       data-bind="click: function() {respondToAccessRequest('accept')}"
                ><i class="fa fa-plus"></i> ${_("Add")}</button>
                <span data-bind="click: function() {respondToAccessRequest('reject')}, visible: !$root.collapsed()"><i class="fa fa-times fa-2x remove-or-reject"></i></span>
                <button class="btn btn-default btn-sm m-l-md" data-bind="click: function() {respondToAccessRequest('reject')}, visible: $root.collapsed()"><i class="fa fa-times"></i> ${_("Remove")}</button>
            </div>
        </td>
    </tr>
</script>

<%def name="buttonGroup()">
    % if permissions.ADMIN in user['permissions']:
        <div class="m-b-sm">
            <a class="btn btn-danger contrib-button" data-bind="click: cancel, visible: changed">${_("Discard Changes")}</a>
            <a class="btn btn-success contrib-button" data-bind="click: submit, visible: canSubmit">${_("Save Changes")}</a>
        </div>
    % endif
        <div data-bind="foreach: messages">
            <div data-bind="css: cssClass, text: text"></div>
        </div>
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}

    <script type="text/javascript">
      window.contextVars = window.contextVars || {};
      window.contextVars.currentUser = window.contextVars.currentUser || {};
      window.contextVars.currentUser.permissions = ${ user['permissions'] | sjson, n } ;
      window.contextVars.isRegistration = ${ node['is_registration'] | sjson, n };
      window.contextVars.contributors = ${ contributors | sjson, n };
      window.contextVars.accessRequests = ${ access_requests | sjson, n };
      window.contextVars.adminContributors = ${ adminContributors | sjson, n };
      window.contextVars.analyticsMeta = $.extend(true, {}, window.contextVars.analyticsMeta, {
          pageMeta: {
              title: 'Contributors',
              public: false,
          },
      });
    </script>

    <script src=${"/static/public/js/sharing-page.js" | webpack_asset}></script>

</%def>

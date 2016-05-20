<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Contributors</%def>

<%include file="project/modal_generate_private_link.mako"/>
<%include file="project/modal_add_contributor.mako"/>
<%include file="project/modal_remove_contributor.mako"/>
<%include file="modal_mailing_list_contributors.mako"/>

<div class="page-header  visible-xs">
  <h2 class="text-300">Contributors</h2>
</div>

<div class="col-md-3 col-xs-12">
    <div class="filters">
        <input type="text" class="form-control searchable" id="nameSearch" placeholder="Filter by name"/>
        <h5 class="m-t-md">Permissions
                <i class="fa fa-question-circle permission-info"
                    data-toggle="popover"
                    data-title="Permission Information"
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i></h5>
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
        <h5 class="m-t-md">Bibliographic Contributor
                <i class="fa fa-question-circle visibility-info"
                    data-toggle="popover"
                    data-title="Bibliographic Contributor Information"
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i></h5>

        <div class="btn-group btn-group-justified-vertical filtergroup" id='visibleFilter'>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id='visible'>Bibliographic</button>
            </div>
            <div class="btn-group">
                <button class="filter-btn btn-default btn" id='notVisible'>Non-Bibliographic</button>
            </div>
        </div>
    </div>
</div>

<div class="col-md-9 col-xs-12">
    <div id="manageContributors" class="scripted">
        <h3> Contributors
            <!-- ko if: canEdit -->
                <a href="#addContributors" data-toggle="modal" class="btn btn-success btn-sm m-l-md">
                  <i class="fa fa-plus"></i> Add
                </a>
            <!-- /ko -->
            % if node['mailing_list_enabled']:
                <span class="m-l-md pull-right" style="font-size: 65%">Mailing List Info: 
                <a data-toggle="modal" data-target="#mailingListContributorsModal"><i class="fa fa-envelope"></i></a>
                </span>
            % endif
        </h3>

        % if 'admin' in user['permissions'] and not node['is_registration']:
            <p class="m-b-xs">Drag and drop contributors to change listing order.</p>
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
                        admins: 'Administrator',
                        write: 'Read + Write',
                        read: 'Read'
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
        No contributors found
    </div>
    <span id="adminContributorsAnchor" class="project-page anchor"></span>
    <div id="adminContributors" data-bind="if: adminContributors().length">
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
        <div id="noAdminContribs" data-bind="visible: $root.adminEmpty" class="text-danger no-items m-b-md">
            No administrators from parent project found.
        </div>
    </div>
        ${buttonGroup()}
    </div>

    % if 'admin' in user['permissions']:
        <h3 class="m-t-xl">View-only Links
            <a href="#addPrivateLink" data-toggle="modal" class="btn btn-success btn-sm m-l-md">
              <i class="fa fa-plus"></i> Add
            </a>
        </h3>
        <p>Create a link to share this project so those who have the link can view&mdash;but not edit&mdash;the project.</p>
        <div class="scripted" id="linkScope">
            <table id="privateLinkTable" class="table responsive-table responsive-table-xs"
                    data-bind="visible: visible">
                <thead>
                    <tr>
                        <th class="responsive-table-hide">Link Name</th>
                        <th class="shared-comp">Shared Components</th>
                        <th>Created Date</th>
                        <th>Created By</th>
                        <th class="min-width">Anonymous</th>
                        <th class="min-width"></th>
                    </tr>
                </thead>
                <tbody data-bind="template: {
                            name: 'linkTbl',
                            foreach: privateLinks,
                            afterRender: afterRenderLink
                        }">
                </tbody>
            </table>
        </div>
    % endif
</div>

<link rel="stylesheet" href="/static/css/pages/contributor-page.css">

<script id="linkTbl" type="text/html">
    <tr>
        <td data-bind="attr: {class: expanded() ? 'expanded' : null,
                                role: $root.collapsed() ? 'button' : null},
                       click: $root.collapsed() ? toggleExpand : null">
            <span class="link-name m-b-xs" data-bind="text: name"></span>
            <span data-bind="attr: {class: expanded() ? 'fa toggle-icon fa-angle-up' : 'fa toggle-icon fa-angle-down'}"></span>
            <div>
                <div class="btn-group">
                    <button title="Copy to clipboard" class="btn btn-default btn-sm m-r-xs copy-button"
                            data-bind="attr: {'data-clipboard-text': linkUrl}" >
                        <i class="fa fa-copy"></i>
                    </button>
                    <input class="link-url" type="text" data-bind="value: linkUrl, attr:{readonly: readonly}, click: toggle, clickBubble: false"  />
                </div>
            </div>
        </td>
        <td>
            <div class="header" data-bind="visible: $root.collapsed() && expanded()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || expanded()">
                <ul class="private-link-list narrow-list" data-bind="foreach: nodesList">
                    <li data-bind="style:{marginLeft: $data.scale}">
                        <span data-bind="getIcon: $data.category"></span>
                        <a data-bind="text:$data.title, attr: {href: $data.url}"></a>
                    </li>
                </ul>
            </div>
        </td>
        <td>
            <div class="header" data-bind="visible: $root.collapsed() && expanded()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || expanded()">
                <span class="link-create-date" data-bind="text: dateCreated.local, tooltip: {title: dateCreated.utc}"></span>
            </div>
        </td>
        <td>
            <div class="header" data-bind="visible: $root.collapsed() && expanded()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || expanded()">
                <a data-bind="text: creator.fullname, attr: {href: creator.url}" class="overflow-block"></a>
            </div>
        </td>
        <td>
            <div class="header" data-bind="visible: $root.collapsed() && expanded()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || expanded()">
                <span data-bind="html: anonymousDisplay"></span>
            </div>
        </td>
        <td>
            <div class="td-content" data-bind="visible: expanded() || !$root.collapsed()">
                <button data-bind="click:  $root.removeLink" type="button" class="btn btn-danger to-top-element">Remove</button>
            </div>
        </td>
    </tr>
</script>

<script id="contribTable" type="text/html">
    <thead>
        <tr>
            <th class="responsive-table-hide"
                data-bind="css: {sortable: ($data === 'contrib' && $root.isSortable())}">Name
            </th>
            <th></th>
            % if node['mailing_list_enabled']:
                <th class="col-md-3" style="text-align: center">
                    In Mailing List
                    <i class="fa fa-question-circle mailing-list-info"
                        data-toggle="popover"
                        data-title="Mailing List Information"
                        data-container="body"
                        data-placement="right"
                        data-html="true"
                    ></i>
                </th>
            % endif
            <th>
                Permissions
                <i class="fa fa-question-circle permission-info"
                    data-toggle="popover"
                    data-title="Permission Information"
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i>
            </th>
            <th class="biblio-contrib">
                Bibliographic Contributor
                <i class="fa fa-question-circle visibility-info"
                    data-toggle="popover"
                    data-title="Bibliographic Contributor Information"
                    data-container="body"
                    data-placement="right"
                    data-html="true"
                ></i>
            </th>
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

<script id="contribRow" type="text/html">
    <tr data-bind="visible: !contributor.filtered(), click: unremove, css: {'contributor-delete-staged': $parent.deleteStaged}, attr: {class: $parent}">
        <td data-bind="attr: {class: contributor.expanded() ? 'expanded' : null,
                                role: $root.collapsed() ? 'button' : null},
                       click: $root.collapsed() ? toggleExpand : null">
            <!-- ko if: ($parent === 'contrib' && $root.isSortable()) -->
                <span class="fa fa-bars sortable-bars"></span>
                <img class="m-l-xs" data-bind="attr: {src: contributor.gravatar_url}" />
            <!-- /ko -->
            <!-- ko ifnot: ($parent === 'contrib' && $root.isSortable()) -->
                <img data-bind="attr: {src: contributor.gravatar_url}" />
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
        % if node['mailing_list_enabled']:
            <td class="text-center">
                <i class="fa fa-check" data-bind="visible: subscribed"></i>
                <i class="fa fa-close" data-bind="visible: !subscribed"></i>
            </td>
        % endif
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
        <td class="text-center">
            <div class="header" data-bind="visible: contributor.expanded() && $root.collapsed()"></div>
            <div class="td-content" data-bind="visible: !$root.collapsed() || contributor.expanded()">
                <input
                    type="checkbox" class="biblio visible-filter"
                    data-bind="checked: visible, enable: $data.canEdit() && !contributor.isAdmin && !deleteStaged()"
                />
            </div>
        </td>
        <td>
            <div class="td-content" data-bind="visible: !$root.collapsed() || contributor.expanded()">
                <!-- ko if: (contributor.canEdit() || canRemove) -->
                        <button href="#removeContributor" class="btn btn-danger btn-sm m-l-md"
                           data-bind="click: remove"
                           data-toggle="modal">Remove</button>
                <!-- /ko -->
            </div>
        </td>
    </tr>
</script>

<%def name="buttonGroup()">
    % if 'admin' in user['permissions']:
        <div class="m-b-sm">
            <a class="btn btn-danger contrib-button" data-bind="click: cancel, visible: changed">Discard Changes</a>
            <a class="btn btn-success contrib-button" data-bind="click: submit, visible: canSubmit">Save Changes</a>
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
      window.contextVars.user = ${ user | sjson, n };
      window.contextVars.isRegistration = ${ node['is_registration'] | sjson, n };
      window.contextVars.contributors = ${ contributors | sjson, n };
      window.contextVars.adminContributors = ${ adminContributors | sjson, n };
    </script>

    <script src=${"/static/public/js/sharing-page.js" | webpack_asset}></script>

</%def>

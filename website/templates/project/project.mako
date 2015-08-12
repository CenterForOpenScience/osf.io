<%inherit file="project/project_base.mako"/>

<%
    is_project = node['node_type'] == 'project'
%>

<div id="projectScope">
    <header class="subhead" id="overview">
        <div class="row">
            <div class="col-sm-6 col-md-7 cite-container">
                % if parent_node['exists']:
                    % if parent_node['can_view'] or parent_node['is_public'] or parent_node['is_contributor']:
                        <h2 class="node-parent-title">
                            <a href="${parent_node['url']}">${parent_node['title']}</a> &nbsp;/
                        </h2>
                    % else:
                        <h2 class="node-parent-title unavailable">
                            <span>Private Project</span>&nbsp;/
                        </h2>
                    % endif
                % endif
                <h2 class="node-title">
                    <span id="nodeTitleEditable" class="overflow">${node['title']}</span>
                </h2>
            </div>
            <div class="col-sm-6 col-md-5">
                <div class="btn-toolbar node-control pull-right"
                    % if not user_name:
                        data-bind="tooltip: {title: 'Log-in or create an account to watch/duplicate this project', placement: 'bottom'}"
                    % endif
                        >
                    <div class="btn-group">
                    % if not node["is_public"]:
                        <button class='btn btn-default disabled'>Private</button>
                        % if 'admin' in user['permissions'] and not node['pending_embargo']:
                            <a class="btn btn-default" data-bind="click: makePublic">Make Public</a>
                        % endif
                    % else:
                        % if 'admin' in user['permissions'] and not node['is_registration']:
                            <a class="btn btn-default" data-bind="click: makePrivate">Make Private</a>
                        % endif
                        <button class="btn btn-default disabled">Public</button>
                    % endif
                    </div>
                    <!-- ko if: canBeOrganized -->
                    <div class="btn-group" style="display: none;" data-bind="visible: true">

                        <!-- ko ifnot: inDashboard -->
                           <a id="addDashboardFolder" data-bind="click: addToDashboard, tooltip: {title: 'Add to Dashboard Folder',
                            placement: 'bottom', container : 'body'}" class="btn btn-default">
                               <i class="fa fa-folder-open"></i>
                               <i class="fa fa-plus"></i>
                           </a>
                        <!-- /ko -->
                        <!-- ko if: inDashboard -->
                           <a id="removeDashboardFolder" data-bind="click: removeFromDashboard, tooltip: {title: 'Remove from Dashboard Folder',
                            placement: 'bottom', container : 'body'}" class="btn btn-default">
                               <i class="fa fa-folder-open"></i>
                               <i class="fa fa-minus"></i>
                           </a>
                        <!-- /ko -->

                    </div>
                    <!-- /ko -->
                    <div class="btn-group">
                        <a
                        % if user_name and (node['is_public'] or user['has_read_permissions']) and not node['is_registration']:
                            data-bind="click: toggleWatch, tooltip: {title: watchButtonAction, placement: 'bottom', container : 'body'}"
                            class="btn btn-default" data-container="body"
                        % else:
                            class="btn btn-default disabled"
                        % endif
                            href="#">
                            <i class="fa fa-eye"></i>
                            <span data-bind="text: watchButtonDisplay" id="watchCount"></span>
                        </a>
                    </div>
                    <div class="btn-group">
                        <a
                        % if user_name:
                            class="btn btn-default"
                            data-bind="tooltip: {title: 'Duplicate', placement: 'bottom', container : 'body'}"
                            data-target="#duplicateModal" data-toggle="modal"
                        % else:
                            class="btn btn-default disabled"
                        % endif
                            href="#">
                            <span class="glyphicon glyphicon-share"></span>&nbsp; ${ node['templated_count'] + node['fork_count'] + node['points'] }
                        </a>
                    </div>
                    % if 'badges' in addons_enabled and badges and badges['can_award']:
                        <div class="btn-group">
                            <button class="btn btn-primary" id="awardBadge" style="border-bottom-right-radius: 4px;border-top-right-radius: 4px;">
                                <i class="fa fa-plus"></i> Award
                            </button>
                        </div>
                    % endif
                </div>
            </div>
        </div>
        <div id="contributors" class="row" style="line-height:25px">
            <div class="col-sm-12">
                % if user['is_contributor']:
                    <a class="link-dashed" href="${node['url']}contributors/">Contributors</a>:
                % else:
                    Contributors:
                % endif

                % if node['anonymous'] and not node['is_public']:
                    <ol>Anonymous Contributors</ol>
                % else:
                    <ol>
                        <div mod-meta='{
                            "tpl": "util/render_contributors.mako",
                            "uri": "${node["api_url"]}get_contributors/",
                            "replace": true
                        }'></div>

                    </ol>
                % endif
                % if node['is_fork']:
                    <br />Forked from <a class="node-forked-from" href="/${node['forked_from_id']}/">${node['forked_from_display_absolute_url']}</a> on
                    <span data-bind="text: dateForked.local, tooltip: {title: dateForked.utc}"></span>
                % endif
                % if node['is_registration'] and node['registered_meta']:
                    <br />Registration Supplement:
                    % for meta in node['registered_meta']:
                        <a href="${node['url']}register/${meta['name_no_ext']}">${meta['name_clean']}</a>
                    % endfor
                % endif
                % if node['is_registration']:
                    <br />Date Registered:
                    <span data-bind="text: dateRegistered.local, tooltip: {title: dateRegistered.utc}" class="date node-date-registered"></span>
                % endif
                    <br />Date Created:
                    <span data-bind="text: dateCreated.local, tooltip: {title: dateCreated.utc}" class="date node-date-created"></span>
                % if not node['is_registration']:
                    | Last Updated:
                    <span data-bind="text: dateModified.local, tooltip: {title: dateModified.utc}" class="date node-last-modified-date"></span>
                % endif
                <span data-bind="if: hasIdentifiers()" class="scripted">
                  <br />
                    Identifiers:
                    DOI <a href="#" data-bind="text: doi, attr.href: doiUrl"></a> |
                    ARK <a href="#" data-bind="text: ark, attr.href: arkUrl"></a>
                </span>
                <span data-bind="if: canCreateIdentifiers()" class="scripted">
                  <!-- ko if: idCreationInProgress() -->
                    <br />
                      <i class="fa fa-spinner fa-lg fa-spin"></i>
                        <span class="text-info">Creating DOI and ARK. Please wait...</span>
                  <!-- /ko -->

                  <!-- ko ifnot: idCreationInProgress() -->
                  <br />
                  <a data-bind="click: askCreateIdentifiers, visible: !idCreationInProgress()">Create DOI / ARK</a>
                  <!-- /ko -->
                </span>
                <br />Category: <span class="node-category">${node['category']}</span>
                &nbsp;
                <span data-bind="css: icon"></span>
                % if node['description'] or 'write' in user['permissions']:
                    <br /><span id="description">Description:</span> <span id="nodeDescriptionEditable" class="node-description overflow" data-type="textarea">${node['description']}</span>
                % endif
            </div>
        </div>

    </header>
</div>


<%def name="title()">${node['title']}</%def>

<%include file="project/modal_add_pointer.mako"/>

<%include file="project/modal_add_component.mako"/>

% if user['can_comment'] or node['has_comments']:
    <%include file="include/comment_template.mako"/>
% endif

<div class="row">

    <div class="col-sm-6 osf-dash-col">

        %if user['show_wiki_widget']:
            <div id="addonWikiWidget" class="" mod-meta='{
            "tpl": "../addons/wiki/templates/wiki_widget.mako",
            "uri": "${node['api_url']}wiki/widget/"
        }'></div>
        %endif

        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Files</h3>
                <div class="pull-right">
                   <a href="${node['url']}files/"> <i class="fa fa-external-link"></i> </a>
                </div>
            </div>
            <div class="panel-body">
                <div id="treeGrid">
                    <div class="spinner-loading-wrapper">
                        <div class="logo-spin text-center"><img src="/static/img/logo_spin.png" alt="loader"> </div>
                         <p class="m-t-sm fg-load-message"> Loading files...  </p>
                    </div>
                </div>
            </div>
        </div>

        % if addons:
            <!-- Show widgets in left column if present -->
            % for addon in addons_enabled:
                % if addons[addon]['has_widget']:
                    %if addon != 'wiki': ## We already show the wiki widget at the top
                    <div class="addon-widget-container" mod-meta='{
                            "tpl": "../addons/${addon}/templates/${addon}_widget.mako",
                            "uri": "${node['api_url']}${addon}/widget/"
                        }'></div>
                    %endif
                % endif
            % endfor
        % else:
            <!-- If no widgets, show components -->
            ${children()}
        % endif

    </div>

    <div class="col-sm-6 osf-dash-col">

        <!-- Citations -->
        % if not node['anonymous']:

         <div class="citations panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title"  style="padding-top: 3px">Citation</h3>
                <div class="pull-right">
                    <span class="permalink">${node['display_absolute_url']}</span><button class="btn btn-link project-toggle"><i class="fa fa-angle-down"></i></button>
                </div>
            </div>
            <div class="panel-body" style="display:none">
                <dl id="citationList" class="citation-list">
                    <dt>APA</dt>
                        <dd class="citation-text" data-bind="text: apa"></dd>
                    <dt>MLA</dt>
                        <dd class="citation-text" data-bind="text: mla"></dd>
                    <dt>Chicago</dt>
                        <dd class="citation-text" data-bind="text: chicago"></dd>
                </dl>
                <p><strong>More</strong></p>
                <div id="citationStylePanel" class="citation-picker">
                    <input id="citationStyleInput" type="hidden" />
                </div>
                <pre id="citationText" class="formatted-citation"></pre>
            </div>
         </div>
        % endif

        <!-- Show child on right if widgets -->
        % if addons:
            ${children()}
        % endif


        %if node['tags'] or 'write' in user['permissions']:
         <div class="tags panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Tags </h3>
                <div class="pull-right">
                </div>
            </div>
            <div class="panel-body">
                <input name="node-tags" id="node-tags" value="${','.join([tag for tag in node['tags']]) if node['tags'] else ''}" />
            </div>
        </div>

        %endif


        <%include file="log_list.mako" args="scripted=True" />

    </div>

</div>

<%def name="children()">
% if ('write' in user['permissions'] and not node['is_registration']) or node['children']:
    <div class="components panel panel-default">
        <div class="panel-heading clearfix">
            <h3 class="panel-title" style="padding-bottom: 5px; padding-top: 5px;">Components </h3>
            <div class="pull-right">
                % if 'write' in user['permissions'] and not node['is_registration']:
                    <a class="btn btn-sm btn-default" data-toggle="modal" data-target="#newComponent">Add Component</a>
                    <a class="btn btn-sm btn-default" data-toggle="modal" data-target="#addPointer">Add Links</a>
                % endif
            </div>
        </div><!-- end addon-widget-header -->
        <div class="panel-body">
            % if node['children']:
                <div id="containment">
                    <div mod-meta='{
                        "tpl": "util/render_nodes.mako",
                        "uri": "${node["api_url"]}get_children/",
                        "replace": true,
                        "kwargs": {
                          "sortable" : ${'true' if not node['is_registration'] else 'false'},
                          "pluralized_node_type": "components"
                        }
                      }'></div>
                </div><!-- end containment -->
            % else:
              <p>No components have been added to this ${node['node_type']}.</p>
            % endif
        </div><!-- end addon-widget-body -->
    </div><!-- end components -->
%endif

</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    % for style in addon_widget_css:
    <link rel="stylesheet" href="${style}" />
    % endfor
    % for stylesheet in tree_css:
    <link rel='stylesheet' href='${stylesheet}' type='text/css' />
    % endfor

    <link rel="stylesheet" href="/static/css/pages/project-page.css">
</%def>

<%def name="javascript_bottom()">

${parent.javascript_bottom()}

% for script in tree_js:
<script type="text/javascript" src="${script | webpack_asset}"></script>
% endfor

<script type="text/javascript">
    // Hack to allow mako variables to be accessed to JS modules
    window.contextVars = $.extend(true, {}, window.contextVars, {
        currentUser: {
            name: ${ user_full_name | sjson, n },
            canComment: ${ user['can_comment'] | sjson, n },
            canEdit: ${ user['can_edit'] | sjson, n }
        },
        node: {
            hasChildren: ${ node['has_children'] | sjson, n },
            isRegistration: ${ node['is_registration'] | sjson, n },
            tags: ${ node['tags'] | sjson, n }
        }
    });
</script>

<script src="${"/static/public/js/project-dashboard.js" | webpack_asset}"></script>

% for asset in addon_widget_js:
<script src="${asset | webpack_asset}"></script>
% endfor

</%def>

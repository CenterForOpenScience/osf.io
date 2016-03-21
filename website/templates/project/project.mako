<%inherit file="project/project_base.mako"/>
<%include file="project/nodes_privacy.mako"/>

<%
    is_project = node['node_type'] == 'project'
%>

<div id="projectScope">
    <header class="subhead" id="overview">
        <div class="row">
            <div class="col-sm-5 col-md-7 cite-container">
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
                    % if node['institution']['name'] and enable_institutions and not node['anonymous']:
                        <a href="/institutions/${node['institution']['id']}"><img class="img-circle" height="75" width="75" id="instLogo" src="${node['institution']['logo_path']}"></a>
                    % endif
                    <span id="nodeTitleEditable" class="overflow">${node['title']}</span>
                </h2>
            </div>
            <div class="col-sm-7 col-md-5">
                <div class="btn-toolbar node-control pull-right"
                    % if not user_name:
                        data-bind="tooltip: {title: 'Log-in or create an account to watch/duplicate this project', placement: 'bottom'}"
                    % endif
                        >
                    <div class="btn-group">
                    % if not node["is_public"]:
                        <button class='btn btn-default disabled'>Private</button>
                        % if 'admin' in user['permissions'] and not node['is_pending_registration'] and not node['embargo_end_date']:
                            <a class="btn btn-default"  href="#nodesPrivacy" data-toggle="modal" >Make Public</a>
                        % endif
                    % else:
                        % if 'admin' in user['permissions'] and not node['is_registration']:
                            <a class="btn btn-default" href="#nodesPrivacy" data-toggle="modal">Make Private</a>
                        % endif
                        <button class="btn btn-default disabled">Public</button>
                    % endif
                    </div>
                    <!-- ko if: canBeOrganized -->
                    <div class="btn-group" style="display: none;" data-bind="visible: true">

                        <!-- ko ifnot: inDashboard -->
                           <a id="addDashboardFolder" data-bind="click: addToDashboard, tooltip: {title: 'Add to bookmarks',
                            placement: 'bottom', container : 'body'}" class="btn btn-default">
                               <i class="fa fa-bookmark"></i>
                               <i class="fa fa-plus"></i>
                           </a>
                        <!-- /ko -->
                        <!-- ko if: inDashboard -->
                           <a id="removeDashboardFolder" data-bind="click: removeFromDashboard, tooltip: {title: 'Remove from bookmarks',
                            placement: 'bottom', container : 'body'}" class="btn btn-default">
                               <i class="fa fa-bookmark"></i>
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
                <div id="contributorsList" style="height: 25px; overflow: hidden">
                % if user['is_contributor']:
                    <a class="link-dashed" href="${node['url']}contributors/">Contributors</a>:
                % else:
                    Contributors:
                % endif

                % if node['anonymous']:
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
                </div>
                % if enable_institutions and not node['anonymous']:
                    % if user['is_contributor'] and not node['is_registration']:
                        <a class="link-dashed" href="${node['url']}settings/#configureInstitutionAnchor" id="institution">Affiliated Institution:</a>
                    % else:
                        Affiliated institution:
                    % endif
                    % if node['institution']['id']:
                        <a href="/institutions/${node['institution']['id']}">${node['institution']['name']}</a>
                    % else:
                        <span> None </span>
                    % endif
                % endif
                % if node['is_fork']:
                    <p>
                    Forked from <a class="node-forked-from" href="/${node['forked_from_id']}/">${node['forked_from_display_absolute_url']}</a> on
                    <span data-bind="text: dateForked.local, tooltip: {title: dateForked.utc}"></span>
                    </p>
                % endif
                % if node['is_registration']:
                    <p>
                    Registration Supplement:
                    % for meta_schema in node['registered_schemas']:
                    <a href="${node['url']}register/${meta_schema['id']}">${meta_schema['schema_name']}</a>
                      % if len(node['registered_schemas']) > 1:
                      ,
                      % endif
                    % endfor
                    </p>
                % endif
                % if node['is_registration']:
                    <p>
                    Date registered:
                    <span data-bind="text: dateRegistered.local, tooltip: {title: dateRegistered.utc}" class="date node-date-registered"></span>
                    </p>
                % endif
                    <p>
                    Date created:
                    <span data-bind="text: dateCreated.local, tooltip: {title: dateCreated.utc}" class="date node-date-created"></span>
                    % if not node['is_registration']:
                        | Last Updated:
                        <span data-bind="text: dateModified.local, tooltip: {title: dateModified.utc}" class="date node-last-modified-date"></span>
                    % endif
                    </p>
                <span data-bind="if: hasIdentifiers()" class="scripted">
                  <br />
                    Identifiers:
                  DOI <span data-bind="text: doi"></span> |
                  ARK <span data-bind="text: ark"></span>
                </span>
                <span data-bind="if: canCreateIdentifiers()" class="scripted">
                  <!-- ko if: idCreationInProgress() -->
                    <p>
                      <i class="fa fa-spinner fa-lg fa-spin"></i>
                        <span class="text-info">Creating DOI and ARK. Please wait...</span>
                    </p>
                  <!-- /ko -->

                  <!-- ko ifnot: idCreationInProgress() -->
                  <p>
                  <a data-bind="click: askCreateIdentifiers, visible: !idCreationInProgress()">Create DOI / ARK</a>
                  </p>
                  <!-- /ko -->
                </span>
                <p>
                Category: <span class="node-category">${node['category']}</span>
                &nbsp;
                <span data-bind="css: icon"></span>
                </p>

                % if (node['description']) or (not node['description'] and 'write' in user['permissions'] and not node['is_registration']):
                    <p>
                    <span id="description">Description:</span> <span id="nodeDescriptionEditable" class="node-description overflow" data-type="textarea">${node['description']}</span>
                    </p>
                % endif
                % if ('admin' in user['permissions'] or node['license'].get('name', 'No license') != 'No license'):
                    <p>
                      <license-picker params="saveUrl: '${node['update_url']}',
                                              saveMethod: 'PUT',
                                              license: window.contextVars.node.license,
                                              saveLicenseKey: 'node_license',
                                              readonly: ${ node['is_registration'] | sjson, n}">
                        <span id="license">License:</span>
                        <span class="text-muted"> ${node['license'].get('name', 'No license')} </span>
                      </license-picker>
                    </p>
                 % endif

            </div>
        </div>

    </header>
</div>


<%def name="title()">${node['title']}</%def>

<%include file="project/modal_add_pointer.mako"/>

<%include file="project/modal_add_component.mako"/>

% if user['can_comment'] or node['has_comments']:
    <%include file="include/comment_pane_template.mako"/>
% endif

<div class="row">

    <div class="col-sm-6 osf-dash-col">

        %if user['show_wiki_widget']:
            <div id="addonWikiWidget" class="" mod-meta='{
            "tpl": "../addons/wiki/templates/wiki_widget.mako",
            "uri": "${node['api_url']}wiki/widget/"
        }'></div>
        %endif

        <!-- Files -->
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
                        <div class="logo-spin logo-lg"></div>
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
                <div id="citationList" class="m-b-md">
                    <div class="citation-list">
                        <div class="f-w-xl">APA</div>
                            <span data-bind="text: apa"></span>
                        <div class="f-w-xl m-t-md">MLA</div>
                            <span data-bind="text: mla"></span>
                        <div class="f-w-xl m-t-md">Chicago</div>
                            <span data-bind="text: chicago"></span>
                        <div data-bind="validationOptions: {insertMessages: false, messagesOnModified: false}, foreach: citations">
                            <!-- ko if: view() === 'view' -->
                                <div class="f-w-xl m-t-md">{{name}}
                                    % if 'admin' in user['permissions'] and not node['is_registration']:
                                        <!-- ko ifnot: $parent.editing() -->
                                            <button class="btn btn-default btn-sm" data-bind="click: function() {edit($parent)}"><i class="fa fa-edit"></i> Edit</button>
                                            <button class="btn btn-danger btn-sm" data-bind="click: function() {removeSelf($parent)}"><i class="fa fa-trash-o"></i> Remove</button>
                                        <!-- /ko -->
                                    % endif
                                </div>
                                <span data-bind="text: text"></span>
                            <!-- /ko -->
                            <!-- ko if: view() === 'edit' -->
                                <div class="f-w-xl m-t-md">Citation name</div>
                                <input data-bind="if: name !== undefined, value: name" placeholder="Required" class="form-control"/>
                                <div class="f-w-xl m-t-sm">Citation</div>
                                <textarea data-bind="if: text !== undefined, value: text" placeholder="Required" class="form-control" rows="4"></textarea>
                                <div data-bind="visible: showMessages, css: 'text-danger'">
                                    <p class="m-t-sm" data-bind="validationMessage: name"></p>
                                    <p class="m-t-sm" data-bind="validationMessage: text"></p>
                                </div>
                                <div class="m-t-md">
                                    <button class="btn btn-default" data-bind="click: function() {cancel($parent)}">Cancel</button>
                                    <button class="btn btn-success" data-bind="click: function() {save($parent)}">Save</button>
                                </div>
                            <!-- /ko -->
                        </div>
                    </div>
                    ## Disable custom citations for now
                    ## % if 'admin' in user['permissions'] and not node['is_registration']:
                    ##     <!-- ko ifnot: editing() -->
                    ##     <button data-bind="ifnot: editing(), click: addAlternative" class="btn btn-default btn-sm m-t-md"><i class="fa fa-plus"></i> Add Citation</button>
                    ##     <!-- /ko -->
                    ## % endif
                </div>
                <p><strong>Get more citations</strong></p>
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

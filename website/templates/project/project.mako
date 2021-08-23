<%inherit file="project/project_base.mako"/>
<%namespace name="render_nodes" file="util/render_nodes.mako" />
<%namespace name="contributor_list" file="util/contributor_list.mako" />
<%namespace name="render_addon_widget" file="util/render_addon_widget.mako" />
<%include file="project/nodes_privacy.mako"/>

<%
    is_project = node['node_type'] == 'project'
%>

<div id="projectScope">
    <header class="subhead" id="overview">
        <div class="row no-gutters">
            <div class="col-lg-6 col-md-12 cite-container">
                % if parent_node['exists']:
                    % if parent_node['can_view'] or parent_node['is_public'] or parent_node['is_contributor_or_group_member']:
                        <h2 class="node-parent-title">
                            <a href="${parent_node['url']}">${parent_node['title']}</a> &nbsp;/
                        </h2>
                    % else:
                        <h2 class="node-parent-title unavailable">
                            <span>Private Project</span>&nbsp;/
                        </h2>
                    % endif
                % endif

                % if node['institutions'] != [] and enable_institutions and not node['anonymous']:
                    <div id="instLogo"></div>
                % endif

                <h2 class="node-title" style="float: left;">
                    <span id="nodeTitleEditable" class="overflow">${node['title']}</span>
                </h2>
            </div>
            <div class="clearfix visible-md-block"></div>
            <div class="col-lg-6">
                <div class="btn-toolbar node-control pull-right">
                    <div class="btn-group">
                        % if node.get('storage_limit_status') and node['storage_limit_status']['text'] and permissions.WRITE in user['permissions']:
                            <a href="https://help.osf.io/hc/en-us/articles/360054528874-OSF-Storage-Caps"  target="_blank" class="btn ${node['storage_limit_status']['class']}"  data-toggle="tooltip" data-placement="bottom" title="This project/component is ${node['storage_limit_status']['text']} the storage limit for OSF Storage. To learn more about limits and alternative storage options click on this icon."><i class="fa fa-exclamation-triangle"></i></a>
                        % endif

                        % if node.get('storage_usage'):
                            <button class="btn disabled" data-toggle="tooltip" data-placement="bottom" title="This is the amount of OSF Storage used for this project.">${node['storage_usage']}</button>
                        % endif
                    </div>
                    <div class="btn-group">
                    % if not node["is_public"]:
                        <button class="btn btn-default disabled">Private</button>
                        % if permissions.ADMIN in user['permissions'] and not (node['is_pending_registration'] or node['is_pending_embargo']) and not (node['is_embargoed'] and parent_node['exists']):
                        <a disabled data-bind="attr: {'disabled': false}, css: {'disabled': nodeIsPendingEmbargoTermination}" class="btn btn-default" href="#nodesPrivacy" data-toggle="modal">
                          Make Public
                          <!-- ko if: nodeIsPendingEmbargoTermination -->
                          <span class="fa fa-info-circle hidden" data-bind="css: {'hidden': false}, tooltip: {title: makePublicTooltip, placement: 'bottom', disabled: true}"></span>
                          <!-- /ko -->
                        </a>
                        % endif
                    % else:
                        % if node.get('storage_limit_status') and permissions.ADMIN in user['permissions'] and not node['is_registration'] and not node['storage_limit_status']['canMakePrivate']:
                            <a class="storage-disabled btn btn-default" data-toggle="tooltip" style="opacity: .65;" data-placement="bottom" title="You cannot make your project private because you are above the storage limit for a private project.">Make Private</a>
                        % elif permissions.ADMIN in user['permissions'] and not node['is_registration']:
                            <a class="btn btn-default" href="#nodesPrivacy" data-toggle="modal">Make Private</a>
                        % endif
                        <button class="btn btn-default disabled">Public</button>
                    % endif
                    </div>
                    <div class="btn-group"
                        % if not user_name:
                            data-bind="tooltip: {title: 'Log in or create an account to duplicate this project', placement: 'top'}"
                        % endif
                        >
                            <div class="dropdown">
                                <a
                                % if user_name:
                                    class="btn btn-default dropdown-toggle" data-toggle="dropdown" type="button" aria-expanded="false"
                                % else:
                                    class="btn btn-default disabled"
                                % endif
                                >
                                    <i class="fa fa-code-fork"></i>&nbsp; ${ node['fork_count'] }
                                </a>
                                <ul class="duplicate-menu dropdown-menu" role="menu">
                                    <div class="arrow-up m-b-xs"></div>
                                    % if not disk_saving_mode:
                                    <li class="p-h-md">
                                        <span class="btn btn-primary btn-block m-t-sm form-control${ '' if user_name and (user['is_contributor_or_group_member'] or node['is_public']) else ' disabled'}"
                                           data-dismiss="modal"
                                           onclick="NodeActions.forkNode();"
                                        >
                                            ${ language.FORK_ACTION | n }
                                        </span>
                                    </li>
                                    %endif
                                    <li class="p-h-md">
                                        <span class="btn btn-primary btn-block m-t-sm form-control${'' if user_name and (user['is_contributor_or_group_member'] or node['is_public']) else ' disabled'}"
                                           onclick="NodeActions.useAsTemplate();"
                                        >
                                            ${ language.TEMPLATE_ACTION | n }
                                        </span>
                                    </li>
                                    % if not disk_saving_mode:
                                    <li class="p-h-md">
                                        <span class="btn btn-primary btn-block m-v-sm" onclick="NodeActions.redirectForkPage();">
                                            View Forks (${ node['fork_count']})
                                        </span>
                                    </li>
                                    %endif
                                </ul>
                            </div> <!-- end .dropdown -->
                        </div><!-- end .btn-group -->
                    <div class="btn-group">
                        <div class="generic-dropdown dropdown pull-right">
                            <button id="otherActionsButton" class="btn btn-default dropdown-toggle disabled" type="button" data-toggle="dropdown">
                                <i class="fa fa-ellipsis-h"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-right">
                                <li data-bind="visible: canBeOrganized()" class="keep-open">
                                    <a role="button" href="#" id="addDashboardFolder" data-bind="visible: !inDashboard(), click: addToDashboard">
                                        Bookmark
                                    </a>
                                    <a role="button" href="#" id="removeDashboardFolder" data-bind="visible: inDashboard(), click: removeFromDashboard">
                                        Remove from bookmarks
                                    </a>
                                </li>
                                % if permissions.ADMIN in user['permissions'] and not node['is_registration']:  ## Create view-only link
                                    <li>
                                        <a href="${node['url']}settings/#createVolsAnchor">
                                            Create view-only link
                                        </a>
                                    </li>
                                % endif ## End create view-only link
                                % if node['is_public']:
                                    <li class="keep-open" id="shareButtonsPopover">
                                        <a href="#" role="button">
                                            Share
                                        </a>
                                    </li>
                                %endif
                                % if node['access_requests_enabled'] and not user['is_contributor_or_group_member'] and not node['is_registration']:
                                    <li data-bind="css: {'keep-open': user.username}">
                                        <a role="button" href="#" data-bind="
                                                        visible: user.username,
                                                        click: requestAccess.requestProjectAccess,
                                                        text: requestAccess.requestAccessButton,
                                                        css: {'disabled': requestAccess.accessRequestPendingOrDenied()},
                                                        tooltip: {title: requestAccess.accessRequestTooltip(),'disabled': true, 'placement': 'left'}">
                                        </a>
                                        <a data-bind="visible: !user.username" role="button" class="btn btn-block" href="${login_url}" >Log in to request access</a>
                                    </li>
                                % endif
                            </ul>
                        </div><!-- end .dropdown -->
                    </div><!-- end .btn-group -->
                </div>
            </div>
        </div>
        <div id="contributors" class="row" style="line-height:25px">
            <div class="col-sm-12">
                <div id="contributorsList" style="height: 25px; overflow: hidden">
                % if user['is_contributor_or_group_member']:
                    <a class="link-dashed" href="${node['url']}contributors/">Contributors</a>:
                % else:
                    Contributors:
                % endif

                % if node['anonymous']:
                    <ol>Anonymous Contributors</ol>
                % else:
                    <ol>
                        ${contributor_list.render_contributors_full(contributors=node['contributors'])}
                    </ol>
                % endif
                </div>
                % if node['groups']:
                    <div>
                        Groups:
                        %for i, group_name in enumerate(node['groups']):
                            <ol>
                                % if i == len(node['groups']) - 1:
                                    ${group_name}
                                % else:
                                    ${group_name},
                                % endif
                            </ol>
                        %endfor
                    </div>
                % endif
                % if enable_institutions and not node['anonymous']:
                    % if (permissions.ADMIN in user['permissions'] and not node['is_registration']) and (len(node['institutions']) != 0 or len(user['institutions']) != 0):
                        <a class="link-dashed" href="${node['url']}settings/#configureInstitutionAnchor" id="institution">Affiliated Institutions:</a>
                        % if node['institutions'] != []:
                            % for inst in node['institutions']:
                                % if inst != node['institutions'][-1]:
                                    <span><a href="/institutions/${inst['id']}">${inst['name']}</a>, </span>
                                % else:
                                    <a href="/institutions/${inst['id']}">${inst['name']}</a>
                                % endif
                            % endfor
                        % else:
                            <span> None </span>
                        % endif
                    % endif
                    % if not (permissions.ADMIN in user['permissions'] and not node['is_registration']) and node['institutions'] != []:
                        Affiliated institutions:
                        % for inst in node['institutions']:
                            % if inst != node['institutions'][-1]:
                                <span><a href="/institutions/${inst['id']}">${inst['name']}</a>, </span>
                            % else:
                                <a href="/institutions/${inst['id']}">${inst['name']}</a>
                            % endif
                        % endfor
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
                <span data-bind="if: hasDoi()" class="scripted">
                  <p>
                    <span data-bind="text:identifier"></span>:
                  DOI <span data-bind="text: doi"></span>
                      <span data-bind="if: hasArk()" class="scripted">| ARK <span data-bind="text: ark"></span></span>
                  </p>
                </span>
                <span data-bind="if: canCreateIdentifiers()" class="scripted">
                  <!-- ko if: idCreationInProgress() -->
                    <p>
                      <i class="fa fa-spinner fa-lg fa-spin"></i>
                        <span class="text-info">Creating DOI. Please wait...</span>
                    </p>
                  <!-- /ko -->

                  <!-- ko ifnot: idCreationInProgress() -->
                  <p>
                  <a data-bind="click: askCreateIdentifiers, visible: !idCreationInProgress()">Create DOI</a>
                  </p>
                  <!-- /ko -->
                </span>
                <p>
                    Category: <span data-bind="css: icon"></span>
                    <span id="nodeCategoryEditable">${node['category']}</span>
                </p>

                % if (node['description']) or (not node['description'] and permissions.WRITE in user['permissions'] and not node['is_registration']):
                    <p>
                    <span id="description">Description:</span> <span id="nodeDescriptionEditable" class="node-description overflow" data-type="textarea">
                        ${node['description']}</span>
                    </p>
                % endif
                <div class="row">
                    % if not node['is_registration']:
                        <div class="col-xs-12">
                    % else:
                        <div class="col-xs-6">
                    % endif
                            % if (permissions.ADMIN in user['permissions'] or node['license'].get('name', 'No license') != 'No license'):
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
                        % if node['is_registration']:
                            <div class="col-xs-6">
                                % if len(node['registered_schemas']) == 1:
                                    <a class="btn btn-primary pull-right" href="${node['url']}register/${node['registered_schemas'][0]['id']}">View Registration Form</a>
                                % else:
                                    ## This is a special case that is right now only possible on 12 Nodes in production
                                    <div class="dropdown">
                                        <button class="btn btn-primary dropdown-toggle pull-right" type="button" id="RegFormMenu" data-toggle="dropdown">
                                            View Registration Forms
                                            <span class="caret"></span>
                                        </button>
                                        <ul class="dropdown-menu pull-right">
                                            % for meta_schema in node['registered_schemas']:
                                                <li><a href="${node['url']}register/${meta_schema['id']}">${meta_schema['schema_name']}</a></li>
                                            % endfor
                                        </ul>
                                    </div>
                                % endif
                            </div>
                    % endif
                </div>
            </div>
        </div>

    </header>
</div>


<%def name="title()">${node['title']}</%def>

<%include file="project/modal_add_pointer.mako"/>

% if (user['can_comment'] or node['has_comments']) and not node['anonymous']:
    <%include file="include/comment_pane_template.mako"/>
% endif

% if node['is_collected']:
    <div class="collections-container">
    % for i, collection in enumerate(node['collections'][:5]):
    <div class="row">
        <div class="col-xs-12">
            <div style="margin-top: 5px;">
                Included in <a href="${collection['url']}" target="_blank">${collection['title']}</a>
                <img style="margin: 0px 0px 2px 5px;" height="16", width="16" src="${collection['logo']}">
                % if permissions.ADMIN in user['permissions']:
                  <a href="${collection['url']}${node['id']}/edit"><i class="fa fa-edit" aria-label="Edit in Collection"></i></a>
                % endif
            &nbsp;<span id="metadata${i}-toggle" class="fa bk-toggle-icon fa-angle-down" data-toggle="collapse" data-target="#metadata${i}"></span>
            </div>
            <div id="metadata${i}" class="collection-details collapse">
                <ul style="margin-left: 30px; padding: 0; margin-bottom: 0;" class="list-unstyled">

                    % if collection['type']:
                      <li>Type:&nbsp;&nbsp;<b>${collection['type']}</b></li>
                    % endif

                    % if collection['status']:
                      <li>Status:&nbsp;&nbsp;<b>${collection['status']}</b></li>
                    % endif

                    % if collection['volume']:
                      <li>Volume:&nbsp;&nbsp;<b>${collection['volume']}</b></li>
                    % endif

                    % if collection['issue']:
                      <li>Issue:&nbsp;&nbsp;<b>${collection['issue']}</b></li>
                    % endif

                    % if collection['program_area']:
                      <li>Program Area:&nbsp;&nbsp;<b>${collection['program_area']}</b></li>
                    % endif

                    % if collection['subjects']:
                      <li>
                        <dl class="dl-horizontal dl-subjects">
                          <dt>Subjects:&nbsp;&nbsp;</dt>
                          <dd>
                          % for subject in collection['subjects']:
                            <span class='subject-preview'>
                              <small> ${subject} </small>
                            </span>
                          % endfor
                          </dd>
                        </dl>
                      </li>
                    % endif
                </ul>
            </div>
        </div>
    </div>
    % endfor
    </div>
% endif

% for i, preprint in enumerate(node['visible_preprints']):
<div class="row">
   <div class="col-xs-12 col-md-6" style="margin-bottom:5px;">
       <div style="margin-top: 5px; margin-bottom: 5px;">
           Has supplemental materials for <a href="${preprint['url']}" target="_blank">${preprint['title']}</a>
           on ${preprint['provider']['name']}
         % if user['is_admin_parent_contributor_or_group_member'] or user['is_contributor_or_group_member']:
            &nbsp;<span id="metadatapreprint${i}-toggle" class="fa bk-toggle-icon fa-angle-down" data-toggle="collapse" data-target="#metadatapreprint${i}"></span>
        % endif
       </div>
       % if user['is_admin_parent_contributor_or_group_member'] or user['is_contributor_or_group_member']:
           <div id="metadatapreprint${i}" class="collection-details collapse">
               <ul style="margin-left: 30px; padding: 0; margin-bottom: 5;" class="list-unstyled">
                    <li>
                        Status:&nbsp;&nbsp;
                            <b>
                                % if preprint['is_withdrawn']:
                                    Withdrawn
                                % else:
                                    ${preprint['state'].capitalize()}
                                % endif
                            </b>
                        % if preprint['is_moderated'] and not preprint['is_withdrawn']:
                            <% icon_tooltip = ''%>
                            % if preprint['state'] == 'pending':
                                % if preprint['provider']['workflow'] == 'post-moderation':
                                    <% icon_tooltip = 'This {preprint_word} is publicly available and searchable but is subject to' \
                                    ' removal by a moderator.'.format(preprint_word=preprint['word'])%>
                                % else:
                                    <% icon_tooltip = 'This {preprint_word} is not publicly available or searchable until approved ' \
                                    'by a moderator.'.format(preprint_word=preprint['word'])%>
                                % endif
                            % elif preprint['state'] == 'accepted':
                                <% icon_tooltip = 'This {preprint_word} is publicly available and searchable.'.format(preprint_word=preprint['word'])%>
                            % else:
                                <% icon_tooltip = 'This {preprint_word} is not publicly available or searchable.'.format(preprint_word=preprint['word'])%>
                            % endif
                            <i class="fa fa-question-circle text-muted" data-toggle="tooltip" data-placement="bottom" title="${icon_tooltip}"></i>
                        % endif
                    </li>
               </ul>
           </div>
         % endif
   </div>
</div>
% endfor


<div class="row">

    <div class="col-sm-12 col-md-6 osf-dash-col">

        %if user['show_wiki_widget']:
            ${ render_addon_widget.render_addon_widget('wiki', addons_widget_data['wiki']) }
        %endif

        <!-- Files -->
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Files</h3>
                <div class="pull-right">
                   <a href="${node['url']}files/"> <i class="fa fa-external-link"></i> </a>
                </div>
            </div>
            % if not node['is_registration'] and not node['anonymous'] and permissions.WRITE in user['permissions']:
                <div class="row">
                    <div class="col-sm-12 m-t-sm m-l-md">
                        <span class="f-w-xl">Click on a storage provider or drag and drop to upload</span>
                    </div>
                </div>
               <div class="panel-body panel-body-with-instructions">
            %else:
               <div class="panel-body">
            %endif
                    <div id="treeGrid">
                        <div class="spinner-loading-wrapper">
                            <div class="ball-scale ball-scale-blue">
                                <div></div>
                            </div>
                             <p class="m-t-sm fg-load-message"> Loading files...  </p>
                        </div>
                    </div>
                </div><!-- end .panel-body -->


        </div>

        % if addons:
            <!-- Show widgets in left column if present -->
            % for addon in addons_enabled:
                % if addons[addon]['has_widget']:
                    %if addon != 'wiki': ## We already show the wiki widget at the top
                        ${ render_addon_widget.render_addon_widget(addon, addons_widget_data[addon]) }
                    %endif
                % endif
            % endfor
        % else:
            <!-- If no widgets, show components -->
            ${children()}
        % endif

    </div>

    <div class="col-sm-12 col-md-6 osf-dash-col">

        <!-- Citations -->
        % if not node['anonymous']:

         <div class="citations panel panel-default">
             <div class="panel-heading clearfix">
                <h3 class="panel-title"  style="padding-top: 3px">Citation</h3>
                <div class="pull-right">
                    <button class="btn btn-link project-toggle"><i class="fa fa-angle-down"></i></button>
                </div>
             </div>
             <div id="citationList">
                 <div class="panel-body" style="display: none;">
                     <div data-bind="visible: page() == 'loading'">
                        <div class="spinner-loading-wrapper">
                            <div class="ball-scale ball-scale-blue">
                                <div></div>
                            </div>
                            <p class="m-t-sm fg-load-message"> Loading citations...  </p>
                        </div>
                     </div>
                     <div data-bind="visible: page() == 'standard'" style="display: none;">
                         % if not node['anonymous'] and permissions.ADMIN in user['permissions']:
                             <a data-bind="click: showEditBox" class="pull-right"><i class="glyphicon glyphicon-pencil"></i> Customize</a>
                         % endif
                         <div class="m-b-md">
                             <div class="citation-list">
                                 <div class="f-w-xl">APA</div>
                                 <span data-bind="text: apa"></span>
                                 <div class="f-w-xl m-t-md">MLA</div>
                                 <span data-bind="text: mla"></span>
                                 <div class="f-w-xl m-t-md">Chicago</div>
                                 <span data-bind="text: chicago"></span>
                             </div>
                         </div>
                         <p><strong>Get more citations</strong></p>
                         <div id="citationStylePanel" class="citation-picker">
                             <input id="citationStyleInput" type="hidden" />
                         </div>
                         <pre id="citationText" class="formatted-citation"></pre>
                     </div>
                     <div data-bind="visible: page() == 'custom'" style="display: none;">
                         % if not node['anonymous'] and permissions.ADMIN in user['permissions']:
                            <a data-bind="click: showEditBox" class="pull-right"><i class="glyphicon glyphicon-pencil"></i> Edit</a>
                         % endif

                         <div class="m-b-md">
                             <div class="citation-list">
                                 <div class="row">
                                     <div class="col-xs-1">
                                         <span id="custom-citation-copy-button" type="button" data-bind="attr: {'data-clipboard-text': customCitation}" class="btn btn-sm btn-default"><i class="fa fa-copy"></i></span>
                                     </div>
                                     <div class="col-xs-9 m-l-sm">
                                         <div class="f-w-xl">Cite as:</div>
                                         <span data-bind="text: customCitation"></span>
                                     </div>
                                 </div>
                             </div>
                         </div>
                     </div>
                     <div data-bind="visible: page() == 'edit'" style="display: none;">
                         <div class="row">
                             <div class="col-md-12 form-group">
                                 <textarea class="form-control"
                                           placeholder="Enter custom citation"
                                           data-bind="value: customCitation, valueUpdate: 'afterkeydown'"
                                           type="text">

                                 </textarea>
                             </div>
                         </div>
                         <div class=" pull-right" role="group">
                             <button type="button" data-bind="click: cancelCitation" class="btn btn-sm btn-default">Cancel</button>
                             <button type="button" data-bind="click: clearCitation, disable: disableRemove" class="btn btn-sm btn-danger">Remove</button>
                             <button type="button" data-bind="click: saveCitation, disable: disableSave" class="btn btn-sm btn-success">Save</button>
                         </div>
                     </div>
                 </div>
             </div>
         </div>
        % endif

        <!-- Show child on right if widgets -->
        % if addons:
            ${children()}
        % endif


        %if node['tags'] or permissions.WRITE in user['permissions']:
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

        <!-- Recent Activity (Logs) -->
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Recent Activity</h3>
            </div>
            <div class="panel-body">
                <div id="logFeed">
                    <div class="spinner-loading-wrapper">
                        <div class="ball-scale ball-scale-blue">
                            <div></div>
                        </div>
                         <p class="m-t-sm fg-load-message"> Loading logs...  </p>
                    </div>
                </div>
            </div>
        </div>

    </div>

</div>

<%def name="children()">
% if (permissions.WRITE in user['permissions'] and not node['is_registration']) or node['children']:
    <div class="components panel panel-default">
        <div class="panel-heading clearfix">
            <h3 class="panel-title" style="padding-bottom: 5px; padding-top: 5px;">Components </h3>
            <div class="pull-right">
                % if permissions.WRITE in user['permissions'] and not node['is_registration']:
                    <span id="newComponent">
                        <button class="btn btn-sm btn-default" disabled="true">Add Component</button>
                    </span>
                    <a class="btn btn-sm btn-default" id="linkProjects" role="button" data-toggle="modal" data-target="#addPointer">Link Projects</a>
                % endif
            </div>
        </div><!-- end addon-widget-header -->
        <div class="panel-body">
            % if node['children']:
                <div id="containment">
                    ${render_nodes.render_nodes(nodes=node['descendants'], sortable=user['can_sort'], user=user, pluralized_node_type='components', show_path=False, include_js=True)}
                </div>
            % else:
              <p class="text-muted">Add components to organize your project.</p>
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
            canEdit: ${ user['can_edit'] | sjson, n },
            canEditTags: ${ user['can_edit_tags'] | sjson, n },
        },
        node: {
            id: ${node['id'] | sjson, n},
            isRegistration: ${ node['is_registration'] | sjson, n },
            tags: ${ node['tags'] | sjson, n },
            institutions: ${node['institutions'] | sjson, n},
        },
        storageRegions: ${ storage_regions | sjson, n },
        storageFlagIsActive: ${ storage_flag_is_active | sjson, n },
        nodeCategories: ${ node_categories | sjson, n },
        analyticsMeta: {
            pageMeta: {
                title: 'Home',
                public: true,
            },
        },
        customCitations: ${ custom_citations | sjson, n },
        currentUserRequestState: ${ user['access_request_state'] | sjson, n }
    });
</script>

<script src="${"/static/public/js/project-dashboard.js" | webpack_asset}"></script>

% for asset in addon_widget_js:
<script src="${asset | webpack_asset}"></script>
% endfor

</%def>

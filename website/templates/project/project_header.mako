<%
    import json
    is_project = node['node_type'] == 'project'
%>
% if node['is_registration']:
    <div class="alert alert-info">This ${node['node_type']} is a registration of <a class="alert-link" href="${node['registered_from_url']}">this ${node['node_type']}</a>; the content of the ${node['node_type']} has been frozen and cannot be edited.
    </div>
    <style type="text/css">
    .watermarked {
        background-image:url('/static/img/read-only.png');
        background-repeat:repeat;
    }
    </style>
% endif
% if node['anonymous'] and user['is_contributor']:
    <div class="alert alert-info">This ${node['node_type']} is being viewed through an anonymized, view-only link. If you want to view it as a contributor, click <a class="alert-link" href="${node['redirect_url']}">here</a>.</div>
% endif
% if node['link'] and not node['is_public'] and not user['is_contributor']:
    <div class="alert alert-info">This ${node['node_type']} is being viewed through a private, view-only link. Anyone with the link can view this project. Keep the link safe.</div>
% endif
% if disk_saving_mode:
    <div class="alert alert-info"><strong>NOTICE: </strong>Forks, registrations, and uploads will be temporarily disabled while the OSF undergoes a hardware upgrade. These features will return shortly. Thank you for your patience.</div>
% endif
<div id="projectScope">
    <header class="subhead" id="overview">
        <div class="row">
            <div class="col-sm-6 col-md-7 cite-container">
                % if parent_node['id']:
                    % if parent_node['can_view'] or parent_node['is_public'] or parent_node['is_contributor']:
                        <h1 class="node-parent-title">
                            <a href="${parent_node['url']}">${parent_node['title']}</a>&nbsp;/
                        </h1>
                    % else:
                        <h1 class="node-parent-title unavailable">
                            <span>Private Project</span>&nbsp;/
                        </h1>
                    % endif
                % endif
                <h1 class="node-title">
                    <span id="nodeTitleEditable" class="overflow">${node['title']}</span>
                </h1>
            </div>
            <div class="col-sm-6 col-md-5">
                <div class="btn-toolbar node-control pull-right">
                    <div class="btn-group">
                    % if not node["is_public"]:
                        <button class='btn btn-default disabled'>Private</button>
                        % if 'admin' in user['permissions']:
                            <a class="btn btn-default" data-bind="click: makePublic">Make Public</a>
                        % endif
                    % else:
                        % if 'admin' in user['permissions']:
                            <a class="btn btn-default" data-bind="click: makePrivate">Make Private</a>
                        % endif
                        <button class="btn btn-default disabled">Public</button>
                    % endif
                    </div>
                    <!-- ko if: canBeOrganized -->
                    <div class="btn-group" style="display: none" data-bind="visible: true">

                        <!-- ko ifnot: inDashboard -->
                           <a data-bind="click: addToDashboard, tooltip: {title: 'Add to Dashboard Folder',
                            placement: 'bottom'}" class="btn btn-default">
                               <i class="icon-folder-open"></i>
                               <i class="icon-plus"></i>
                           </a>
                        <!-- /ko -->
                        <!-- ko if: inDashboard -->
                           <a data-bind="click: removeFromDashboard, tooltip: {title: 'Remove from Dashboard Folder',
                            placement: 'bottom'}" class="btn btn-default">
                               <i class="icon-folder-open"></i>
                               <i class="icon-minus"></i>
                           </a>
                        <!-- /ko -->

                    </div>
                    <!-- /ko -->
                    <div class="btn-group">
                        <a
                        % if user_name and (node['is_public'] or user['is_contributor']) and not node['is_registration']:
                            data-bind="click: toggleWatch, tooltip: {title: watchButtonAction, placement: 'bottom'}"
                            class="btn btn-default"
                        % else:
                            class="btn btn-default disabled"
                        % endif
                            href="#">
                            <i class="icon-eye-open"></i>
                            <span data-bind="text: watchButtonDisplay" id="watchCount"></span>
                        </a>
                        <a rel="tooltip" title="Duplicate"
                            class="btn btn-default${ '' if is_project else ' disabled'}" href="#"
                            data-toggle="modal" data-target="#duplicateModal">
                            <span class="glyphicon glyphicon-share"></span>&nbsp; ${ node['templated_count'] + node['fork_count'] + node['points'] }
                        </a>
                    </div>
                    % if 'badges' in addons_enabled and badges and badges['can_award']:
                        <div class="btn-group">
                            <button class="btn btn-success" id="awardBadge" style="border-bottom-right-radius: 4px;border-top-right-radius: 4px;">
                                <i class="icon-plus"></i> Award
                            </button>
                        </div>
                    % endif
                </div>
            </div>
        </div>
        <div id="contributors" class="row">
            <div class="col-sm-12">
                Contributors:
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
                <br />Date Created:
                <span data-bind="text: dateCreated.local, tooltip: {title: dateCreated.utc}" class="date node-date-created"></span>
                | Last Updated:
                <span data-bind="text: dateModified.local, tooltip: {title: dateModified.utc}" class="date node-last-modified-date"></span>
                % if parent_node['id']:
                    <br />Category: <span class="node-category">${node['category']}</span>
                % elif node['description'] or 'write' in user['permissions']:
                    <br /><span id="description">Description:</span> <span id="nodeDescriptionEditable" class="node-description overflow" data-type="textarea">${node['description']}</span>
                % endif
            </div>
        </div>
        <nav id="projectSubnav" class="navbar navbar-default" role="navigation">
            <div class="container-fluid">
                <div class="navbar-header">
                    <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target=".project-nav">
                        <span class="sr-only">Toggle navigation</span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                    </button>
                    <a class="navbar-brand visible-xs" href="#">
                        ${'Project' if node['node_type'] == 'project' else 'Component'} Navigation
                    </a>
                </div>
                <div class="collapse navbar-collapse project-nav">
                    <ul class="nav navbar-nav">
                        <li><a href="${node['url']}">Overview</a></li>
                        <li><a href="${node['url']}files/">Files</a></li>
                        <!-- Add-on tabs -->
                        % for addon in addons_enabled:
                            % if addons[addon]['has_page']:
                                <li>
                                    <a href="${node['url']}${addons[addon]['short_name']}">
                                        % if addons[addon]['icon']:
                                            <img src="${addons[addon]['icon']}" class="addon-logo"/>
                                        % endif
                                        ${addons[addon]['full_name']}
                                    </a>
                                </li>
                            % endif
                        % endfor
                        % if node['is_public'] or user['is_contributor']:
                            <li><a href="${node['url']}statistics/">Statistics</a></li>
                        % endif
                        % if not node['is_registration']:
                            <li><a href="${node['url']}registrations/">Registrations</a></li>
                        % endif
                        <li><a href="${node['url']}forks/">Forks</a></li>
                        % if user['is_contributor']:
                            <li><a href="${node['url']}contributors/">Sharing</a></li>
                        % endif
                        % if 'write' in user['permissions']:
                            <li><a href="${node['url']}settings/">Settings</a></li>
                        % endif
                    </ul>
                </div>
            </div>
        </nav>
    </header>
    <script>
        ## TODO: Take this out of the mako file. This was a quick fix and likely not to live for very long, but it's not
        ## the proper way to do it.
        $(function () {
            var path = window.location.pathname;

            $(".project-nav a").each(function () {
                var href = $(this).attr('href');
                if (path === href ||
                   (path.indexOf('files') > -1 && href.indexOf('files') > -1) ||
                   (path.indexOf('wiki') > -1 && href.indexOf('wiki') > -1)) {
                    $(this).closest('li').addClass('active');
                }
            });
        });
    </script>
</div>

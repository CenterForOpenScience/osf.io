<%
    import json
    is_project = node['node_type'] == 'project'
%>

<div id="projectBanner" >
    <header class="subhead" id="overview">
        <nav id="projectSubnav" class="navbar osf-project-navbar" role="navigation">
            <div class="container">

                <div class="navbar-header">
                    <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target=".project-nav">
                        <span class="sr-only">Toggle navigation</span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                    </button>
                    <a class="navbar-brand visible-xs" href="${node['url']}">
                        ${'Project' if node['node_type'] == 'project' else 'Component'} Navigation
                    </a>
                </div>
                <div class="collapse navbar-collapse project-nav">
                    <ul class="nav navbar-nav">
                    % if parent_node['id']:
                        % if parent_node['can_view'] or parent_node['is_public'] or parent_node['is_contributor']:
                            <li><a href="${parent_node['url']}" data-toggle="tooltip" title="${parent_node['title']}" data-placement="bottom" style="padding: 13px 17px;"> <i class="icon icon-level-down rotate-180"></i>  </a></li>
                        % else:
                            <li><a href="#"> <i class="icon icon-level-up text-muted"></i>  </a></li>
                        % endif
                    % endif
                        <li><a href="${node['url']}"  class="project-title"> ${node['title'] | n}  </a></li>
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
                        % if not node['is_registration'] and user['has_read_permissions']:
                            <li><a href="${node['url']}settings/">Settings</a></li>
                        % endif
                    </ul>
                </div>
            </div>
        </nav>
    </header>


    <style type="text/css">
    .watermarked {
        padding-top: 55px;
    }
    </style>

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


</div>

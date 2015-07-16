<%
    is_project = node['node_type'] == 'project'
%>

<div id="projectBanner" >
    <header class="subhead" id="overview">
        <nav id="projectSubnav" class="navbar osf-project-navbar" role="navigation">
            <div class="container">

                <div class="navbar-header">
                    <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target=".project-nav">
                        <span class="sr-only">Toggle navigation</span>
                        <span class="fa fa-bars fa-lg"></span>
                    </button>
                    <a class="navbar-brand visible-xs" href="${node['url']}">
                        ${'Project' if node['node_type'] == 'project' else 'Component'} Navigation
                    </a>
                </div>
                <div class="collapse navbar-collapse project-nav">
                    <ul class="nav navbar-nav">

                    % if parent_node['id']:

                        % if parent_node['can_view'] or parent_node['is_public'] or parent_node['is_contributor']:
                            <li><a href="${parent_node['url']}" data-toggle="tooltip" title="${parent_node['title']}" data-placement="bottom" style="padding: 12px 17px;"> <i class="fa fa-level-down fa-rotate-180"></i>  </a></li>

                        % else:
                            <li><a href="#" data-toggle="tooltip" title="Parent project is private" data-placement="bottom" style="cursor: default"> <i class="fa fa-level-down fa-rotate-180 text-muted"></i>  </a></li>
                        % endif

                    % endif
                        <li><a href="${node['url']}"  class="project-title"> ${node['title'] | n}  </a></li>

                    % if not node['is_retracted']:
                        <li id="projectNavFiles"><a href="${node['url']}files/">Files</a></li>
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

                        % if user['has_read_permissions'] and not node['is_registration'] or (node['is_registration'] and 'admin' in user['permissions']):
                            <li><a href="${node['url']}settings/">Settings</a></li>
                        % endif

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


    % if node['is_registration']:  ## Begin registration undismissable labels

        % if not node['is_retracted']:
            <div class="alert alert-info">This ${node['node_type']} is a registration of <a class="link-solid" href="${node['registered_from_url']}">this ${node['node_type']}</a>; the content of the ${node['node_type']} has been frozen and cannot be edited.
            </div>
            <style type="text/css">
            .watermarked {
                background-image:url('/static/img/read-only.png');
                background-repeat:repeat;
            }
            </style>
        % endif

        % if node['pending_retraction']:
            <div class="alert alert-info">This ${node['node_type']} is currently pending entering into a retracted state.</div>
        % endif

        % if  node['is_retracted']:
            <div class="alert alert-danger">This ${node['node_type']} is a retracted registration of <a class="link-solid" href="${node['registered_from_url']}">this ${node['node_type']}</a>; the content of the ${node['node_type']} has been taken down for the reason(s) stated below.</div>
        % endif

        % if  node['pending_embargo']:
            <div class="alert alert-info">This ${node['node_type']} is currently pending registration, awaiting approval from project administrators. This registration will be final and enter the embargo period when all project administrators approve the registration or 48 hours pass, whichever comes first. The embargo will keep the registration private until the embargo period ends.</div>
        % endif

        % if  node['embargo_end_date']:
            <div class="alert alert-danger">This ${node['node_type']} is currently embargoed. It will remain private until its embargo date, ${ node['embargo_end_date'] }, passes or an admin manually makes it public.</div>
        % endif

    % endif  ## End registration undismissable labels

    % if node['anonymous'] and user['is_contributor']:
        <div class="alert alert-info">This ${node['node_type']} is being viewed through an anonymized, view-only link. If you want to view it as a contributor, click <a class="link-solid" href="${node['redirect_url']}">here</a>.</div>
    % endif

    % if node['link'] and not node['is_public'] and not user['is_contributor']:
        <div class="alert alert-info">This ${node['node_type']} is being viewed through a private, view-only link. Anyone with the link can view this project. Keep the link safe.</div>
    % endif

    % if disk_saving_mode:
        <div class="alert alert-info"><strong>NOTICE: </strong>Forks, registrations, and uploads will be temporarily disabled while the OSF undergoes a hardware upgrade. These features will return shortly. Thank you for your patience.</div>
    % endif

</div>

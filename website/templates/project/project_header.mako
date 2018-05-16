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
                    <span class="navbar-brand visible-xs visible-sm">
                        ${'Project' if node['node_type'] == 'project' else 'Component'} Navigation
                    </span>
                </div>
                <div class="collapse navbar-collapse project-nav">
                    <ul class="nav navbar-nav">

                    % if parent_node['id']:

                        % if parent_node['can_view'] or parent_node['is_public'] or parent_node['is_contributor']:
                            <li><a href="${parent_node['url']}" data-toggle="tooltip" title="${parent_node['title']}" data-placement="bottom"> <i class="fa fa-level-down fa-rotate-180"></i>  </a></li>

                        % else:
                            <li><a href="#" data-toggle="tooltip" title="Parent project is private" data-placement="bottom" style="cursor: default"> <i class="fa fa-level-down fa-rotate-180 text-muted"></i>  </a></li>
                        % endif

                    % endif
                        <li>
                            <a href="${node['url']}"  class="project-title">
                                ${ node['title'] }
                            </a>
                        </li>
                    % if not node['is_retracted']:
                        <li id="projectNavFiles">
                            <a href="${node['url']}files/">
                                Files
                            </a>
                        </li>
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

                        % if project_analytics:
                        % if node['is_public'] or user['is_contributor']:
                            <li><a href="${node['url']}analytics/">Analytics</a></li>
                        % endif
                        % endif

                        % if project_registrations:
                        % if not node['is_registration'] and not node['anonymous']:
                            <li><a href="${node['url']}registrations/">Registrations</a></li>
                        % endif
                        % endif

                        % if user['is_contributor']:
                            <li><a href="${node['url']}contributors/">Contributors</a></li>
                        % endif

                        % if 'write' in user['permissions'] and not node['is_registration']:
                            <li><a href="${node['url']}addons/">Add-ons</a></li>
                        % endif

                        % if user['has_read_permissions'] and not node['is_registration'] or (node['is_registration'] and 'write' in user['permissions']):
                            <li><a href="${node['url']}settings/">Settings</a></li>
                        % endif
                    % endif
                    % if (user['can_comment'] or node['has_comments']) and not node['anonymous']:
                        <li id="commentsLink">
                            <a href="" class="hidden-lg hidden-md cp-handle" data-bind="click:removeCount" data-toggle="collapse" data-target="#projectSubnav .navbar-collapse">
                                Comments
                                <span data-bind="if: unreadComments() !== 0">
                                    <span data-bind="text: displayCount" class="badge"></span>
                                </span>
                           </a>
                       </li>
                    % endif
                    % if 'admin' in user['permissions']:
                       <li id="projectNavTimestamp">
                           <a href="${node['url']}timestamp/">
                              Timestamp
                           </a>
                       </li>
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

    %if maintenance:
        <style type="text/css">
            @media (max-width: 767px) {
                #projectBanner .osf-project-navbar {
                    position: absolute;
                    top: 100px;
                }
            }
        </style>
    %endif

    % if node['is_registration']:  ## Begin registration undismissable labels

        % if not node['is_retracted']:
            % if not node['is_pending_registration']:
                % if file_name and urls.get('archived_from'):
                        <div class="alert alert-info">This file is part of a registration and is being shown in its archived version (and cannot be altered).
                            The <a class="link-solid" href="${urls['archived_from']}">active file</a> is viewable from within the <a class="link-solid" href="${node['registered_from_url']}">live ${node['node_type']}</a>.</div>
                % else:
                    <div class="alert alert-info">This registration is a frozen, non-editable version of <a class="link-solid" href="${node['registered_from_url']}">this ${node['node_type']}</a></div>
                % endif
            % else:
                <div class="alert alert-info">
                    <div>This is a pending registration of <a class="link-solid" href="${node['registered_from_url']}">this ${node['node_type']}</a>, awaiting approval from project administrators. This registration will be final when all project administrators approve the registration or 48 hours pass, whichever comes first.</div>

                    % if 'admin' in user['permissions']:
                        <div>
                            <br>
                            <button type="button" id="registrationCancelButton" class="btn btn-danger" data-toggle="modal" data-target="#registrationCancel">
                                Cancel registration
                            </button>
                        </div>
                        <%include file="modal_confirm_cancel_registration.mako"/>
                    % endif
                </div>
            % endif

            <style type="text/css">
                .watermarked {
                    background-image:url('/static/img/read-only.png');
                    background-repeat:repeat;
                }
            </style>

        % endif

        % if node['is_pending_retraction']:
            <div class="alert alert-info">This ${node['node_type']} is currently pending withdrawal.</div>
        % endif

        % if node['is_retracted']:
            <div class="alert alert-danger">This ${node['node_type']} is a withdrawn registration of <a class="link-solid" href="${node['registered_from_url']}">this ${node['node_type']}</a>; the content of the ${node['node_type']} has been taken down for the reason(s) stated below.</div>
        % endif

        % if node['is_pending_embargo']:
            <div
                class="alert alert-info">This ${node['node_type']} is currently pending registration, awaiting approval from project administrators. This registration will be final and enter the embargo period when all project administrators approve the registration or 48 hours pass, whichever comes first. The embargo will keep the registration private until the embargo period ends.
                % if 'admin' in user['permissions']:
                        <div>
                            <br>
                            <button type="button" id="registrationCancelButton" class="btn btn-danger" data-toggle="modal" data-target="#registrationCancel">
                                Cancel registration
                            </button>
                        </div>
                        <%include file="modal_confirm_cancel_registration.mako"/>
                    % endif
            </div>
        % endif

        % if node['is_embargoed']:
            <div class="alert alert-danger">This registration is currently embargoed. It will remain private until its embargo end date, ${ node['embargo_end_date'] }.</div>
        % endif

    % endif  ## End registration undismissable labels

    % if node['preprint_file_id'] and user['is_contributor'] and not node['is_public'] and node['has_published_preprint']:
        <div class="alert alert-info">This ${node['node_type']} has a preprint, but has been made Private. Make your preprint discoverable by making this ${node['node_type']} Public.</div>
    % endif

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

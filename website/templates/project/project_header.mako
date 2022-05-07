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
                        ${_('Project') if node['node_type'] == 'project' else _('Component')} ${ _("Navigation") }
                    </span>
                </div>
                <div class="collapse navbar-collapse project-nav">
                    <ul class="nav navbar-nav">

                    % if parent_node['id']:

                        % if parent_node['can_view'] or parent_node['is_public'] or parent_node['is_contributor_or_group_member']:
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
                                ${_("Files")}
                            </a>
                        </li>
                        <!-- Add-on tabs  -->
                        % for addon in addons_enabled:

                            % if addon not in ['binderhub', 'metadata'] and addons[addon]['has_page']:
                                <li>
                                    <a href="${node['url']}${addons[addon]['short_name']}">

                                        % if addons[addon]['icon'] and addons[addon]['has_page_icon']:
                                            <img src="${addons[addon]['icon']}" class="addon-logo"/>
                                        % endif
                                        ${addons[addon]['full_name']}
                                    </a>
                                </li>
                            % endif
                        % endfor

                        % if 'metadata' in addons_enabled and addons['metadata']['has_page']:
                            <li>
                                <a href="${node['url']}${addons['metadata']['short_name']}">
                                    % if addons['metadata']['icon'] and addons['metadata']['has_page_icon']:
                                        <img src="${addons['metadata']['icon']}" class="addon-logo"/>
                                    % endif
                                    ${_("Metadata")}
                                </a>
                            </li>
                        % endif

                        % if 'binderhub' in addons_enabled and addons['binderhub']['has_page']:
                            <li>
                                <a href="${node['url']}${addons['binderhub']['short_name']}">
                                    % if addons['binderhub']['icon'] and addons['binderhub']['has_page_icon']:
                                        <img src="${addons['binderhub']['icon']}" class="addon-logo"/>
                                    % endif
                                    ${_("Computation")}
                                </a>
                            </li>
                        % endif

                        % if project_analytics:
                        % if node['is_public'] or user['is_contributor_or_group_member']:
                            <li><a href="${node['url']}analytics/">${ _("Statistics") }</a></li>
                        % endif
                        % endif

                        % if project_registrations:
                        % if not node['is_registration'] and not node['anonymous']:
                            <li><a href="${node['url']}registrations/">${ _("Registrations") }</a></li>
                        % endif
                        % endif

                        % if user['is_contributor_or_group_member']:
                            <li><a href="${node['url']}contributors/">${_("Contributors")}</a></li>
                        % endif

                        % if permissions.WRITE in user['permissions'] and not node['is_registration']:
                            <li><a href="${node['url']}addons/">${ _("Add-ons") }</a></li>
                        % endif

                        % if user['has_read_permissions'] and not node['is_registration'] or (node['is_registration'] and permissions.WRITE in user['permissions']):
                            <li><a href="${node['url']}settings/">${ _("Settings") }</a></li>
                        % endif
                    % endif
                    % if (user['can_comment'] or node['has_comments']) and not node['anonymous']:
                        <li id="commentsLink">
                            <a href="" class="hidden-lg hidden-md cp-handle" data-bind="click:removeCount" data-toggle="collapse" data-target="#projectSubnav .navbar-collapse">
                                ${ _("Comments") }
                                <span data-bind="if: unreadComments() !== 0">
                                    <span data-bind="text: displayCount" class="badge"></span>
                                </span>
                           </a>
                       </li>
                    % endif
                    % if 'admin' in user['permissions']:
                       <li id="projectNavTimestamp">
                           <a href="${node['url']}timestamp/">
                              ${ _("Timestamp") }
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
                        <div class="alert alert-info">${ _("This file is part of a registration and is being shown in its archived version (and cannot be altered).")}
                            ${_("The <a %(archivedFromUrl)s>active file</a> is viewable from within the <a %(registeredFromUrl)s>live %(nodeType)s</a>.") % dict(archivedFromUrl='class="link-solid" href="' + urls['archived_from'] +'"',registeredFromUrl='class="link-solid" href="' + node['registered_from_url'] + '"',nodeType=node['node_type'] ) | n}</div>
                % else:
                    <div class="alert alert-info">${ _('This registration is a frozen, non-editable version of <a %(registeredFromUrl)s>this %(nodeType)s</a>') % dict(registeredFromUrl='class="link-solid" href="' + node['registered_from_url'] + '"',nodeType=node['node_type']) | n}</div>
                % endif
            % else:
                ## Hide top alert message for metadata addon
##                 <div class="alert alert-info">
##                     <div>${ _('This is a pending registration of <a %(registeredFromUrl)s>this %(nodeType)s</a>, awaiting approval from project administrators. This registration will be final when all project administrators approve the registration or 48 hours pass, whichever comes first.') % dict(registeredFromUrl='class="link-solid" href="' + h(node['registered_from_url']) + '"', nodeType=h(node['node_type'])) | n }</div>
##
##                     % if 'permissions.ADMIN' in user['permissions']:
##                         <div>
##                             <br>
##                             <button type="button" id="registrationCancelButton" class="btn btn-danger" data-toggle="modal" data-target="#registrationCancel">
##                                 ${ _("Cancel registration") }
##                             </button>
##                         </div>
##                         <%include file="modal_confirm_cancel_registration.mako"/>
##                     % endif
##                 </div>
            % endif

            <style type="text/css">
                .watermarked {
                    background-image:url('/static/img/read-only.png');
                    background-repeat:repeat;
                }
            </style>

        % endif

        % if node['is_pending_retraction']:
            <div class="alert alert-info">${ _("This %(nodeType)s is currently pending withdrawal.") % dict(nodeType=node['node_type']) }</div>
        % endif

        % if node['is_retracted']:
            <div class="alert alert-danger">${ _('This %(nodeType)s is a withdrawn registration of <a %(registeredFromUrl)s>this %(nodeType)s</a>; the content of the %(nodeType)s has been taken down for the reason(s) stated below.') % dict(nodeType=node['node_type'],registeredFromUrl='class="link-solid" href="' + h(node['registered_from_url']) + '"') | n }</div>
        % endif

        % if node['is_pending_embargo']:
            ## Hide top alert message for metadata addon
##             <div
##                 class="alert alert-info">${ _('This %(nodeType)s is currently pending registration, awaiting approval from project administrators. This registration will be final and enter the embargo period when all project administrators approve the registration or 48 hours pass, whichever comes first. The embargo will keep the registration private until the embargo period ends.') % dict(nodeType=node['node_type']) }
##                 % if permissions.ADMIN in user['permissions']:
##                         <div>
##                             <br>
##                             <button type="button" id="registrationCancelButton" class="btn btn-danger" data-toggle="modal" data-target="#registrationCancel">
##                                 ${ _("Cancel registration") }
##                             </button>
##                         </div>
##                         <%include file="modal_confirm_cancel_registration.mako"/>
##                     % endif
##             </div>
        % endif

        % if node['is_embargoed']:
            <div class="alert alert-danger">${ _('This registration is currently embargoed. It will remain private until its embargo end date, %(embargoEndDate)s.') % dict(embargoEndDate=node['embargo_end_date']) }</div>
        % endif

    % endif  ## End registration undismissable labels

    % if node['is_supplemental_project'] and user['is_contributor_or_group_member'] and not node['is_public']:
        <div class="alert alert-info">${ _('This %(nodeType)s contains supplemental materials for a preprint, but has been made Private. Make your supplemental materials discoverable by making this %(nodeType)s Public.') % dict(nodeType=node['node_type']) }</div>
    % endif

    % if node['anonymous'] and user['is_contributor_or_group_member']:
        <div class="alert alert-info">${ _('This %(nodeType)s is being viewed through an anonymized, view-only link. If you want to view it as a contributor, click <a %(redirectUrl)s>here</a>.') % dict(nodeType=node['node_type'],redirectUrl='class="link-solid" href="' + h(node['redirect_url']) + '"') }</div>
    % endif

    % if node['link'] and not node['is_public'] and not user['is_contributor_or_group_member']:
        <div class="alert alert-info">${ _('This %(nodeType)s is being viewed through a private, view-only link. Anyone with the link can view this project. Keep the link safe.') % dict(nodeType=node['node_type']) }</div>
    % endif

    % if disk_saving_mode:
        <div class="alert alert-info">${ _("<strong>NOTICE: </strong>Forks, registrations, and uploads will be temporarily disabled while the GakuNin RDM undergoes a hardware upgrade. These features will return shortly. Thank you for your patience.") | n }</div>
    % endif

</div>

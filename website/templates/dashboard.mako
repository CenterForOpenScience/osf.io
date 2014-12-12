<%inherit file="base.mako"/>
<%def name="title()">Dashboard</%def>

<%def name="stylesheets()">
<link rel="stylesheet" href="/static/css/typeahead.css">
<link rel="stylesheet" href="/static/css/onboarding.css">
</%def>

<%def name="content()">
% if disk_saving_mode:
    <div class="alert alert-info"><strong>NOTICE: </strong>Forks, registrations, and uploads will be temporarily disabled while the OSF undergoes a hardware upgrade. These features will return shortly. Thank you for your patience.</div>
% endif
<div class="row">
    <div class="col-md-7">
        <div class="project-details"></div>
        <div class="page-header">
            <div class="pull-right"><a class="btn btn-default" href="/folder/${dashboard_id}" id = "${dashboard_id}">New Folder</a></div>
            <h3>Projects</h3>
        </div><!-- end .page-header -->
        <link rel="stylesheet" href="/static/css/projectorganizer.css">

        <div class="project-organizer" id="projectOrganizerScope">
            <%include file="projectGridTemplates.html"/>

            <div id="project-grid"></div>
            <span class='organizer-legend'><img alt="Folder" src="/static/img/hgrid/folder.png">Folder</span>
            <span class='organizer-legend'><img alt="Smart Folder" src="/static/img/hgrid/smart-folder.png">Smart Folder</span>
            <span class='organizer-legend'><img alt="Project" src="/static/img/hgrid/project.png">Project</span>
            <span class='organizer-legend'><img alt="Registration" src="/static/img/hgrid/reg-project.png">Registration</span>
            <span class='organizer-legend'><img alt="Component" src="/static/img/hgrid/component.png">Component</span>
            <span class='organizer-legend'><img alt="Registered Component" src="/static/img/hgrid/reg-component.png">Registered Component</span>
            <span class='organizer-legend'><img alt="Link" src="/static/img/hgrid/pointer.png">Link</span>
        </div><!-- end project-organizer -->
    </div> <!-- end col-md -->

    ## Knockout componenet templates
    <%include file="components/dashboard_templates.mako"/>
    <div class="col-md-5">
        <div class="ob-tab-head" id="obTabHead">
            <ul class="nav nav-tabs" role="tablist">
            <li class="active"><a href="#quicktasks" role="tab" data-toggle="tab">Quick Tasks</a></li>
            <li><a href="#watchlist" role="tab" data-toggle="tab">Watchlist</a></li>
            ## %if 'badges' in addons_enabled:
            ## <li><a href="#badges" role="tab" data-toggle="tab">Badges</a></li>
            ## %endif
            </ul>

        </div><!-- end #obTabHead -->
        <div class="tab-content" >
            <div class="tab-pane active" id="quicktasks">
                <ul class="ob-widget-list"> <!-- start onboarding -->
                    <div id="obGoToProject">
                        <osf-ob-goto params="data: nodes"></osf-ob-goto>
                    </div>
                    <div id="projectCreate">
                        <li id="obNewProject" class="ob-list-item list-group-item">

                            <div data-bind="click: toggle" class="ob-header pointer">
                                <h3
                                    class="ob-heading list-group-item-heading">
                                    Create a project
                                </h3>
                                <i data-bind="css: {'icon-plus': !isOpen(), 'icon-minus': isOpen()}"
                                    class="pointer ob-expand-icon icon-large pull-right">
                                </i>
                            </div><!-- end ob-header -->
                            <div data-bind="visible: isOpen()" id="obRevealNewProject">
                                <osf-project-create-form
                                    params="data: nodes, hasFocus: focus">
                                </osf-project-create-form>
                            </div>
                        </li> <!-- end ob-list-item -->
                    </div>
                    % if not disk_saving_mode:
                    <div id="obRegisterProject">
                        <osf-ob-register params="data: nodes"></osf-ob-register>
                    </div>
                    <div id="obUploader">
                        <osf-ob-uploader params="data: nodes"></osf-ob-uploader>
                    </div>
                    % endif
                </ul> <!-- end onboarding -->
            </div><!-- end .tab-pane -->
            <div class="tab-pane" id="watchlist">
                <%include file="log_list.mako" args="scripted=False"/>
            </div><!-- end tab-pane -->
            ## %if 'badges' in addons_enabled:
                ## <%include file="dashboard_badges.mako"/>
            ## %endif
        </div><!-- end .tab-content -->
    </div><!-- end col-md -->
</div><!-- end row -->
%if 'badges' in addons_enabled:
    <div class="row">
        <div class="col-md-5">
            <div class="page-header">
              <button class="btn btn-success pull-right" id="newBadge" type="button">New Badge</button>
                <h3>Your Badges</h3>
            </div>
            <div mod-meta='{
                     "tpl": "../addons/badges/templates/dashboard_badges.mako",
                     "uri": "/api/v1/dashboard/get_badges/",
                     "replace": true
                }'></div>
        </div><!-- end col-md -->
        <div class="col-md-5">
            <div class="page-header">
                <h3>Badges You've Awarded</h3>
            </div>
        </div><!-- end col-md-->
    </div><!-- end row -->
%endif
</%def>

<%def name="javascript_bottom()">

<script src="/static/public/js/dashboard-page.js"></script>

</%def>

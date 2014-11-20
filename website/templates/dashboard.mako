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

            <div class="hgrid" id="project-grid"></div>
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

<script>
    $script(['/static/js/onboarder.js']);  // exports onboarder
    $script(['/static/js/projectCreator.js']);  // exports projectCreator

    $script.ready(['projectCreator', 'onboarder'], function() {
        // Send a single request to get the data to populate the typeaheads
        var url = "${api_url_for('get_dashboard_nodes')}";
        var request = $.getJSON(url, function(response) {
            var allNodes = response.nodes;
            ##  For uploads, only show nodes for which user has write or admin permissions
            var uploadSelection = ko.utils.arrayFilter(allNodes, function(node) {
                return $.inArray(node.permissions, ['write', 'admin']) !== -1;
            });
            ## Filter out components and nodes for which user is not admin
            var registrationSelection = ko.utils.arrayFilter(uploadSelection, function(node) {
                return node.category === 'project' && node.permissions === 'admin';
            });

            $.osf.applyBindings({nodes: allNodes}, '#obGoToProject');
            % if not disk_saving_mode:
              $.osf.applyBindings({nodes: registrationSelection}, '#obRegisterProject');
              $.osf.applyBindings({nodes: uploadSelection}, '#obUploader');
            % endif

            function ProjectCreateViewModel() {
                var self = this;
                self.isOpen = ko.observable(false),
                self.focus = ko.observable(false);
                self.toggle = function() {
                    self.isOpen(!self.isOpen());
                    self.focus(self.isOpen());
                };
                self.nodes = response.nodes;
            }
            $.osf.applyBindings(ProjectCreateViewModel, '#projectCreate');
        });
        request.fail(function(xhr, textStatus, error) {
            Raven.captureMessage('Could not fetch dashboard nodes.', {
                url: url, textStatus: textStatus, error: error
            });
        });
    });

     // initialize the logfeed
    $script(['/static/js/logFeed.js']);
    $script.ready('logFeed', function() {
        // NOTE: the div#logScope comes from log_list.mako
        var logFeed = new LogFeed("#logScope", "/api/v1/watched/logs/");
    });
</script>

##       Project Organizer
    <script src="/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js"></script>
    <script src="/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js"></script>
    <script>
        $script.ready(['hgrid'], function() {
            $script(['/static/vendor/bower_components/hgrid/plugins/hgrid-draggable/hgrid-draggable.js'],'hgrid-draggable');
        });
        $script(['/static/js/projectorganizer.js']);
        $script.ready(['projectorganizer'], function() {
            var projectbrowser = new ProjectOrganizer('#project-grid');
        });
    </script>
</%def>

<%inherit file="base.mako"/>
<%def name="title()">Dashboard</%def>
<%def name="content()">
<div class="row">
    <div class="col-md-7">
        <div class="project-details"></div>
        <div class="page-header">
            <div class="pull-right"><a class="btn btn-primary" href="/project/new/">New Project</a></div>
            <div class="pull-right"><a class="btn btn-default" href="/folder/${dashboard_id}" id = "${dashboard_id}">New Folder</a></div>
            <h3>Projects</h3>
        </div>
        <link rel="stylesheet" href="/static/css/projectorganizer.css">
        <div id="projectOrganizerScope">
            <%include file="projectGridTemplates.html"/>

            <div class="hgrid" id="project-grid"></div>
            <img src="/static/img/hgrid/folder.png">Folder
            <img src="/static/img/hgrid/smart-folder.png">Smart Folder
            <img src="/static/img/hgrid/project.png">Project
            <img src="/static/img/hgrid/reg-project.png">Registration
            <img src="/static/img/hgrid/component.png">Component
            <img src="/static/img/hgrid/reg-component.png">Registered Component
            <img src="/static/img/hgrid/pointer.png">Link


        </div>


    <%include file='log_templates.mako'/>
    </div>
    <div class="row">
        <div class="col-md-5">
           <div id="watchFeed">
               <div class="page-header">
                    <h3>Watched Projects</h3>
                </div>
                <%include file="log_list.mako"/>
            </div><!-- end #watchFeed -->
        </div>
    </div>
</div>

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
        </div>
        <div class="col-md-5">
            <div class="page-header">
                <h3>Badges You've Awarded</h3>
            </div>
            <div mod-meta='{
                     "tpl": "../addons/badges/templates/dashboard_assertions.mako",
                     "uri": "/api/v1/dashboard/get_assertions/",
                     "replace": true
                }'></div>
        </div>
    </div>
%endif
</%def>

<%def name="javascript_bottom()">

<script>
    // Initialize the LogFeed
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
        $script(['/static/js/handlebars-v1.3.0.js'],'handlebars');
        $script(['/static/js/projectorganizer.js']);
        $script.ready(['projectorganizer'], function() {
            var projectbrowser = new ProjectOrganizer('#project-grid');
        });


    </script>
</%def>

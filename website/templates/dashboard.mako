<%inherit file="base.mako"/>
<%def name="title()">Dashboard</%def>
<%def name="content()">

<%include file="modal_register_project.mako"/>
<link rel="stylesheet" href="/static/css/typeahead.css">

<div class="row">
    <div class="col-md-6">
        <div class="page-header">
            <div class="pull-right"><a class="btn btn-default" href="/project/new">New Project</a></div>
            <h3>Projects</h3>
        </div>
        <div mod-meta='{
                 "tpl": "util/render_nodes.mako",
                 "uri": "/api/v1/dashboard/get_nodes/",
                 "replace": true
            }'></div>
    </div>
    <div class="row">
        <div class="col-md-6">
           <div id="watchFeed">
               <div class="page-header">


########################################################################################################################
                    <h3>I want to...</h3>
                        <div id="logScope">
                    <%include file="log_list.mako"/>
                    <a class="moreLogs" data-bind="click: moreLogs, visible: enableMoreLogs">more</a>
                </div><!-- end #logScope -->

                </div>
                <ul>
                <div id="file_drop">
                    <li node_reference="fks27:node" class="project list-group-item list-group-item-node unavailable">
                    <a class="btn btn-default" href="/project/new">Make a New Project</a>
                    </li>

                    <li node_reference="fks27:node" class="project list-group-item list-group-item-node unavailable">
                    <a class="btn btn-default" href="/project/new">Upload a File</a>
                    </li>

                    <li node_reference="fks27:node" class="project list-group-item list-group-item-node unavailable">
                    <a class="btn btn-default" data-toggle="modal" data-target="#newRegistration">Register a Project</a>
                    </li>
                </ul>

########################################################################################################################

            </div><!-- end #watchFeed -->
        </div>
    </div>
</div>
%if 'badges' in addons_enabled:
    <div class="row">
        <div class="col-md-6">
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
        <div class="col-md-6">
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
        var logFeed = new LogFeed("#logScope", "/api/v1/watched/logs/");
    });
    $script(['/static/js/typeahead.js'],'typeahead');
    $script(['/static/js/projectSearch.js']);
    $script.ready('projectSearch', function() {
        var projectsearch = new ProjectSearch();
    });


</script>
</%def>

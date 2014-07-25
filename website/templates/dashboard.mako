<%inherit file="base.mako"/>
<%def name="title()">Dashboard</%def>
<%def name="content()">

<link rel="stylesheet" href="/static/css/typeahead.css">
<link rel="stylesheet" href="/static/css/onboarding.css">
<link rel="stylesheet" href="/static/vendor/bower_components/jquery-ui/themes/base/jquery-ui.css">

<div class="row">
    <div class="col-md-7">
        <div class="page-header">
            <h3>Projects</h3>
        </div>
        <div mod-meta='{
                 "tpl": "util/render_nodes.mako",
                 "uri": "/api/v1/dashboard/get_nodes/",
                 "replace": true
            }'></div>
    </div>
    <div class="row">
        <div class="col-md-5">
            <div id="obTabHead">
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
                    <ul style="padding:0px;"> <!-- start onboarding -->
                        <%include file="ob_new_project.mako"/> 
                        <%include file="ob_register_project.mako"/> 
                        <%include file="ob_add_file.mako"/> 
                    </ul> <!-- end onboarding -->
                </div>   
                <div class="tab-pane" id="watchlist">
                    <div id="logScope">
                    <%include file="log_list.mako"/>
                    <a class="moreLogs" data-bind="click: moreLogs, visible: enableMoreLogs">more</a>
                </div><!-- end #logScope -->

                </div>
                ## %if 'badges' in addons_enabled:
                   ## <%include file="dashboard_badges.mako"/>
                ## %endif
            </div>
        </div>
    </div>
</div>
</%def>

<%def name="javascript_bottom()">
<script>
    $script(['/static/js/typeahead.js'],'typeahead');
    $script(['/static/js/typeaheadSearch.js'], 'typeaheadSearch');
    
    $script(['/static/js/obAddFile.js']);
    $script.ready('obAddFile', function() {
        var obaddfile = new ObAddFile();
    });
    $script(['/static/js/obNewProject.js']);
    $script(['/static/js/obRegisterProject.js']);
    $script.ready('obRegisterProject', function() {
        var obregisterproject = new ObRegisterProject();
    });

     // Initialize the LogFeed
    $script(['/static/js/logFeed.js']);
    $script.ready('logFeed', function() {
        var logFeed = new LogFeed("#logScope", "/api/v1/watched/logs/");
    });
</script>
</%def>

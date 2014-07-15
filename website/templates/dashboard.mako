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
            <div class="page-header">
                <ul class="nav nav-tabs" role="tablist">
                <li class="active"><a href="#quicktasks" role="tab" data-toggle="tab">Quick Tasks</a></li>
                <li><a href="#watchlist" role="tab" data-toggle="tab">Watchlist</a></li>
                <li><a href="#badges" role="tab" data-toggle="tab">Badges</a></li>
                </ul>

            </div><!-- end #page-header -->
            <div class="tab-content">
                <div class="tab-pane active" id="quicktasks"> <%include file="onboarding.mako"/> </div>
                <div class="tab-pane" id="watchlist">
                    <div id="logScope">
                    <%include file="log_list.mako"/>
                    <a class="moreLogs" data-bind="click: moreLogs, visible: enableMoreLogs">more</a>
                </div><!-- end #logScope -->

                </div>
                <div class="tab-pane" id="badges">...</div>
            </div>
            

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


<!-- this doesn't belong here -->

<%def name="javascript_bottom()">
<script>
// new project js
    $('#obNewProjectBtn').one("click", obOpenNewProject);

    function obOpenNewProject() {
        $('#obRevealNewProject').show();
        $(this).one("click", obCloseNewProject);
        $('#obIconNewProject').attr('src', "/static/img/minus.png")
    }

    function obCloseNewProject() {
        $('#obRevealNewProject').hide();
        $(this).one("click", obOpenNewProject);
        $('#obIconNewProject').attr('src', "/static/img/plus.png")
    }

// TODO(sloria): require('jquery') here
// block the create new project button when the form is submitted
    $('#projectForm').on('submit',function(){
        $('button[type="submit"]', this)
            .attr('disabled', 'disabled')
            .text('Creating');
    });

// new registration js
    $('#obRegisterProjectBtn').one("click", obOpenRegisterProject);

    function obOpenRegisterProject() {
        $('#obRevealRegisterProject').show();
        $(this).one("click", obCloseRegisterProject);
        $('#obIconRegisterProject').attr('src', "/static/img/minus.png")
    }

    function obCloseRegisterProject() {
        $('#obRevealRegisterProject').hide();
        $(this).one("click", obOpenRegisterProject);
        $('#obIconRegisterProject').attr('src', "/static/img/plus.png")
    }

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

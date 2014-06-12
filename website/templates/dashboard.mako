<%inherit file="base.mako"/>
<%def name="title()">Dashboard</%def>
<%def name="content()">

##<%include file="modal_ob_register_project.mako"/>


<link rel="stylesheet" href="/static/css/typeahead.css">
<link rel="stylesheet" href="/static/css/onboarding.css">

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
                    ##<%include file="log_list.mako"/>
                    ##<a class="moreLogs" data-bind="click: moreLogs, visible: enableMoreLogs">more</a>
                </div><!-- end #logScope -->

                </div>
                <ul>
                <div>
                    <li node_reference="fks27:node" class="project list-group-item list-group-item-node unavailable">
                    <div class="onboard_heading">Create a New Project</div>

                    <a class="btn btn-default" id="obNewProjectBtn">Make a New Project</a>
                    <div class="obReveal" id="obRevealNewProject">
                        <%include file="project/new_project_form.mako"/>
                    </div>
                    </li>

                    <li node_reference="fks27:node" class="project list-group-item list-group-item-node unavailable">
                    <div class="onboard_heading">Register a Project</div>

                    <a class="btn btn-default" id="obRegisterProjectBtn">Register a Project</a>
                    <div class="obReveal" id="obRevealRegisterProject">
                        <div id="project-search_register_project">
            
                            <input class="typeahead" type="text" placeholder="Search projects" style="margin:20px;" 
                            id = 'input_project_register_project'>
                            <span class = "findBtn btn btn-default" id="add_link_register_project" disabled="disabled">Go to registration page</span>
                        </div>

                    </div>
                    </li>

                    <li node_reference="fks27:node" class="project list-group-item list-group-item-node unavailable">
                    <div class="onboard_heading">Add a File to a Project</div>
                    <div id="project-search_add_file">
                        
                        <div id="obDropzone">
                        
                        Drop File (or click)
                        
                        </div>
                        <div class="obReveal" id="obDropzoneReveal">
                            <img id="obArrowRight" src="/static/img/triangle_right.png" >
                            <div id="obProjectSearchContainer">
                                <input class="typeahead" type="text" placeholder="Search projects" id = 'input_project_add_file'><br>
                                <span class = "findBtn btn btn-default" id="add_link_add_file" disabled="disabled">Upload file to this project</span>
                            </div>
                        </div>
                    </div>
                </li>

                </ul>

#########################################################################################################################
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


<!-- this doesn't belong here -->

<%def name="javascript_bottom()">
<script>
    $('#obNewProjectBtn').click(function(){
        $('#obRevealNewProject').fadeIn();
        $('#obNewProjectBtn').hide();
    });

    $('#obRegisterProjectBtn').click(function(){
        console.log("this")
        $('#obRevealRegisterProject').fadeIn();
        $('#obRegisterProjectBtn').hide();
    });



    // Initialize the LogFeed
    $script(['/static/js/logFeed.js']);
    $script.ready('logFeed', function() {
        var logFeed = new LogFeed("#logScope", "/api/v1/watched/logs/");
    });
    $script(['/static/vendor/dropzone/dropzone.js'],'dropzone');

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

    

</script>
</%def>

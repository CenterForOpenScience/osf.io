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
                        </div><!-- end #logScope -->
                </div><!-- end #page-header -->
                <ul>

                    <!-- start #ob-new-project -->
                    <li id="ob-new-project" class="ob-list list-group-item">
                        <div id="ob-new-project-btn" class="ob-reveal-btn">
                            <div class="ob-heading" >Create a New Project</div>
                            <img class="ob-expand-icon" id="ob-icon-new-project" src="/static/img/plus.png">
                        </div><!-- end #ob-new-project-btn -->
                        <div class="ob-reveal" id="ob-reveal-new-project">
                            <br> 
                            <%include file="project/new_project_form.mako"/>
                        </div> <!-- end #ob-reveal -->
                    </li> <!-- end #ob-new-project" -->

                    <!-- start #ob-register-project -->
                    <li id="ob-register-project" class="ob-list list-group-item"> 

                        <div id="ob-register-project-btn">
                            <div class="ob-heading" >Register a Project</div>
                            <img class="ob-expand-icon" id="ob-icon-register-project" src="/static/img/plus.png">
                        </div><!-- end #ob-register-project-btn -->

                            <!-- <a class="btn btn-default" id="obRegisterProjectBtn">Register a Project</a> -->
                            <div class="ob-reveal" id="ob-reveal-register-project">
                        <div id="project-search-register-project">
                            <input class="typeahead" type="text" placeholder="Search projects" style="margin:20px;" 
                            id = 'input-project-register-project'>
                            <span class = "findBtn btn btn-default" id="add-link-register-project" disabled="disabled">Go to registration page</span>
                        </div>
                    </div>
                    </li> <!-- end #ob-register-project" -->

                    <!-- start #ob-add-file -->
                    <li class="ob-list list-group-item">
                        <div class="ob-heading">Add a File to a Project</div>
                        <div id="project-search-add-file">
                        <div style="max-width:170px;">
                            <div id="ob-dropzone" class="ob-dropzone-box">
                            Drop File (or click)
                            </div>
                            <!-- <div id="ob-dropzone-selected" class="ob-dropzone-box"> -->
                            <div id="ob-dropzone-selected" class="ob-dropzone-box ob-reveal">
                                    <img id="uploadIcon" src="//:0">
                                    <div id="obDropzoneFilename"> </div>
                                    <progress class="ob-reveal" id="uploadProgress" max="100" value="0"></progress>

                                <div id="clearDropzone"><img src="/static/img/close2.png"></div>
                            </div>
                            
                            </div>

                            <div class="ob-reveal" id="ob-dropzone-reveal">

                                <img id="ob-arrow-right" src="/static/img/triangle_right.png" >
                                <div id="ob-project-search-container">
                                    <input class="typeahead" type="text" placeholder="Search projects" id = 'input-project-add-file'>
                                    <br>                                    
                                    <span class="findBtn btn btn-default" id="add-link-add-file" disabled="disabled">Upload</span>
                                </div>
                            </div>
                        </div>
                    </li> <!-- end #ob-add-file" -->
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
// new project js
    $('#ob-new-project-btn').one("click", obOpenNewProject);

    function obOpenNewProject() {
        $('#ob-reveal-new-project').fadeIn(300);
        $(this).one("click", obCloseNewProject);
        $('#ob-icon-new-project').attr('src', "/static/img/minus.png")
    }

    function obCloseNewProject() {
        $('#ob-reveal-new-project').fadeOut(100);
        $(this).one("click", obOpenNewProject);
        $('#ob-icon-new-project').attr('src', "/static/img/plus.png")
    }

// TODO(sloria): require('jquery') here
//block the create new project button when the form is submitted
    $('#projectForm').on('submit',function(){
        $('button[type="submit"]', this)
            .attr('disabled', 'disabled')
            .text('Creating');
    });

// new registration js
    $('#ob-register-project-btn').one("click", obOpenRegisterProject);

    function obOpenRegisterProject() {
        $('#ob-reveal-register-project').fadeIn(300);
        $(this).one("click", obCloseRegisterProject);
        $('#ob-icon-register-project').attr('src', "/static/img/minus.png")
    }

    function obCloseRegisterProject() {
        $('#ob-reveal-register-project').fadeOut(100);
        $(this).one("click", obOpenRegisterProject);
        $('#ob-icon-register-project').attr('src', "/static/img/plus.png")
    }


    // Initialize the LogFeed
    $script(['/static/js/logFeed.js']);
    $script.ready('logFeed', function() {
        var logFeed = new LogFeed("#logScope", "/api/v1/watched/logs/");
    });
    // $script(['/static/vendor/dropzone/dropzone.js'],'dropzone');

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

<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Files</%def>

<div class="row">
<div class="col-md-12">
    <div class='help-block'>
        % if 'write' in user['permissions'] and not disk_saving_mode:
            <p>To Upload: Drag files from your desktop into a folder below OR click an upload (<button class="btn btn-default btn-mini" disabled><i class="icon-upload-alt"></i></button>) button.</p>
        % endif
    </div>
</div><!-- end col-md-->

</div><!--end row -->
## TODO: This progressbar is used else where; separate into a template include - it's not used here anymore

<div id="treeGrid" class="filebrowser">
<div class="fangorn-loading"> <i class="icon-spinner fangorn-spin"></i> <p class="m-t-sm fg-load-message"> Loading files...  </p> </div>
</div>


<%def name="stylesheets()">
${parent.stylesheets()}
% for stylesheet in tree_css:
<link rel='stylesheet' href='${stylesheet}' type='text/css' />
% endfor
</%def>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
% for script in tree_js:
<script type="text/javascript" src="${script}"></script>
% endfor
<script>
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };


$script.ready(['fangorn'], function() {
    var msg = setInterval(function(){displayMessage()}, 2000);
    var loadingText = [ 'Adjusting Bell Curves',  'Aligning Covariance Matrices', 'Applying Theatre Soda Layer',  'Calculating Llama Expectoration Trajectory',  'Deciding What Message to Display Next',  'Gesticulating Mimes',  'Projecting Law Enforcement Pastry Intake',  'Setting Universal Physical Constants', 'Calibrating warp drive', 'Removing bad memories', 'Reorganizing distribution matrix', 'Validating assumptions', 'Scrambling launch codes', 'Allocating head space', 'Revising life goals', 'Pushing up elephants up the stairs'];
    var used = [];

    function displayMessage() {
        if(used.length === 7){
            used = [];
        }
        var index = pickUnique(); 
        used.push(index);   
        var messageEl = $('.fg-load-message');
        if(messageEl.length > 0){
            messageEl.text(loadingText[index]+'...'); 
        } else {
            stopRefresh();
        }
        console.log("Hey");
    }

    function stopRefresh() {
        clearInterval(msg);
    }

    function pickUnique() {
        var index = Math.floor(Math.random()*15) + 1;
        if(used.indexOf(index) !== -1){
            pickUnique(); 
        }
        else {
            return index;   
        }
    }

    $.ajax({
      url:  nodeApiUrl + 'files/grid/'
    })
    .done(function( data ) {
        console.log("data", data);
        var fangornOpts = {
            placement : 'project-files',
            divID: 'treeGrid',
            filesData: data.data

        };
        console.log("fangorn", Fangorn);
        var filebrowser = new Fangorn(fangornOpts);
    });

});


</script>
</%def>

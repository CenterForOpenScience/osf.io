<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Files</%def>

<div class="row">
<div class="col-md-8">
    <div class='help-block'>
        % if 'write' in user['permissions'] and not disk_saving_mode:
            <p>To Upload: Drag files from your desktop into a folder below OR click an upload (<button class="btn btn-default btn-mini" disabled><i class="icon-upload"></i></button>) button.</p>
        % endif
    </div>
</div><!-- end col-md-->

<div class="col-md-4">
    <input role="search" class="form-control" placeholder="Search files..." type="text" id="fileSearch" autofocus>
</div>
</div><!--end row -->
## TODO: This progressbar is used else where; separate into a template include
<div id="filebrowserProgressBar" class="progress progress-striped active">
    <div class="progress-bar"  role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" style="width: 100%">
        <span class="sr-only">Loading</span>
    </div>
</div>
<div id="myGrid" class="filebrowser hgrid"></div>


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
<script src="/static/public/js/files-page.js"></script>
</%def>

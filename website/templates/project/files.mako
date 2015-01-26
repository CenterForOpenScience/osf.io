<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Files</%def>
<link rel="stylesheet" href="/static/vendor/bower_components/jquery-ui/themes/base/minified/jquery.ui.resizable.min.css">

<div class="page-header  visible-xs">
  <h2 class="text-300">Files</h2>
</div>

<div class="row">
<div class="col-md-12">
    <div class='help-block'>
        % if 'write' in user['permissions'] and not disk_saving_mode:
            <p>To Upload: Drag files from your desktop into a folder below OR click an upload (<i class="btn btn-default btn-xs" disabled><span class="icon-upload-alt"></span></i>) button.</p>
        % endif
    </div>
</div><!-- end col-md-->

</div><!--end row -->

<div id="treeGrid">
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
<script type="text/javascript" src="${script | webpack_asset}"></script>
% endfor
<script src=${"/static/public/js/files-page.js" | webpack_asset}></script>
</%def>

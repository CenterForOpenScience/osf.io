<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Files</%def>

<div class="page-header  visible-xs">
  <h2 class="text-300">Files</h2>
</div>

<div id="treeGrid">
	<div class="spinner-loading-wrapper">
		<div class="logo-spin text-center"><img src="/static/img/logo_spin.png" alt="loader"> </div> 
		<p class="m-t-sm fg-load-message"> Loading files...  </p> 
	</div>
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
    <script type="text/javascript">
        window.contextVars = window.contextVars || {};
        % if 'write' in user['permissions'] and not node['is_registration']:
            window.contextVars.diskSavingMode = !${ disk_saving_mode | sjson, n };
        % endif
    </script>
</%def>

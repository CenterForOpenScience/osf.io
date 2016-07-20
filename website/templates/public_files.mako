<%inherit file="base.mako"/>

<%def name="title()"> ${node['owner_name']}'s Public Files</%def>

<%def name="content()">
<div class="page-header  visible-xs">
</div>
    <h2 class="text-center"> ${node['owner_name']}'s Public Files</h2>

<div id="treeGrid">
	<div class="spinner-loading-wrapper">
		<div class="logo-spin logo-lg"></div>
		<p class="m-t-sm fg-load-message"> Loading files...  </p>
	</div>
</div>

</%def>

<%def name="javascript_bottom()">
<script>
    window.contextVars = $.extend(true, {}, window.contextVars, {
         nodeId : ${ node['node_id'] |sjson, n },
         nodeApiUrl : ${ node['api_url'] | sjson, n },
         isPublicFilesCol : ${node['is_public_files_node']  | sjson, n },
     });
</script>

<script src=${"/static/public/js/publicfiles-page.js" | webpack_asset}></script>
</%def>

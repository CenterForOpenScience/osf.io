<script type="text/html" id="googledrive_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: decodeURIComponent(params.path)"></a> to
Google Drive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="googledrive_folder_created">
created folder
<span class="overflow log-folder" data-bind="text: stripSlash(decodeURIComponent(params.path))"></span> in
Google Drive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="googledrive_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: decodeURIComponent(params.path)"></a> to
Google Drive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="googledrive_file_removed">
removed <span data-bind="text: pathType(params.path) "></span> <span class="overflow" data-bind="text: stripSlash(decodeURIComponent(params.path))"></span> from
Google Drive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="googledrive_folder_selected">
linked Google Drive folder /<span class="overflow" data-bind="text: (params.folder === '/' ? '(Full Google Drive)' : decodeURIComponent(params.folder))"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="googledrive_node_deauthorized">
deauthorized the Google Drive addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="googledrive_node_deauthorized">
Google Drive addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>


<script type="text/html" id="googledrive_node_authorized">
authorized the Google Drive addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="googledrive_node_deauthorized_no_user">
Google Drive addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>

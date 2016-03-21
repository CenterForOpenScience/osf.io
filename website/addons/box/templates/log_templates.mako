<script type="text/html" id="box_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: stripSlash(params.path)"></a> to
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="box_folder_created">
created folder
<span class="overflow log-folder" data-bind="text: stripSlash(params.path)"></span> in
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="box_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: stripSlash(params.path)"></a> to
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="box_file_removed">
removed <span data-bind="text: pathType(params.path) "></span> <span class="overflow" data-bind="text: stripSlash(params.path)"></span> from
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="box_folder_selected">
linked Box folder
<span class="overflow" data-bind="text: (params.folder === 'All Files' ? '/ (Full Box)' : (params.folder || '').replace('All Files',''))"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, title: nodeTitle"></a>
</script>


<script type="text/html" id="box_node_deauthorized">
deauthorized the Box addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="box_node_authorized">
authorized the Box addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="box_node_deauthorized_no_user">
Box addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>

<script type="text/html" id="onedrive_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">
    {{ stripSlash(params.path) }}</a> to
Onedrive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="onedrive_folder_created">
created folder
<span class="overflow log-folder">{{ stripSlash(params.path) }}</span> in
Onedrive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="onedrive_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">
    {{ stripSlash(params.path) }}</a> to
Onedrive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="onedrive_file_removed">
removed {{ pathType(params.path) }} <span class="overflow">
    {{ stripSlash(params.path) }}</span> from
Onedrive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="onedrive_folder_selected">
linked Onedrive folder
<span class="overflow">
    {{ params.folder === 'All Files' ? '/ (Full Onedrive)' : (params.folder || '').replace('All Files','')}}
</span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="onedrive_node_deauthorized">
deauthorized the Onedrive addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="onedrive_node_authorized">
authorized the Onedrive addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

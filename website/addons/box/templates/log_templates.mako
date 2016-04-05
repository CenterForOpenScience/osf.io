<script type="text/html" id="box_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">
    {{ stripSlash(params.path) }}</a> to
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="box_folder_created">
created folder
<span class="overflow log-folder">{{ stripSlash(params.path) }}</span> in
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="box_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">
    {{ stripSlash(params.path) }}</a> to
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="box_file_removed">
removed {{ pathType(params.path) }} <span class="overflow">
    {{ stripSlash(params.path) }}</span> from
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="box_folder_selected">
linked Box folder
<span class="overflow">
    {{ params.folder === 'All Files' ? '/ (Full Box)' : (params.folder || '').replace('All Files','')}}
</span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="box_node_deauthorized">
deauthorized the Box addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="box_node_authorized">
authorized the Box addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="box_node_deauthorized_no_user">
Box addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
    deauthorized
</script>

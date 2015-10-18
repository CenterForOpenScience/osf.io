<script type="text/html" id="sharelatex_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
project
<span data-bind="text: params.project"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="sharelatex_folder_created">
created folder
<span class="overflow log-folder">{{ stripSlash(params.path) }}</span> in
project {{ params.project }} in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="sharelatex_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> in
project
<span data-bind="text: params.project"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="sharelatex_file_removed">
removed {{ pathType(params.path) }} <span class="overflow">{{ stripSlash(params.path) }}</span> from
project
<span data-bind="text: params.project"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="sharelatex_project_linked">
linked the ShareLatex project /
<span data-bind="text: params.project"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="sharelatex_project_unlinked">
un-selected project
<span data-bind="text: params.project"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="sharelatex_node_authorized">
authorized the ShareLatex addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="sharelatex_node_deauthorized">
deauthorized the ShareLatex addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="sharelatex_node_deauthorized_no_user">
ShareLatex addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
    deauthorized
</script>

<script type="text/html" id="dryad_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
dryad repo
<span data-bind="text: params.dryad.user"></span> /
<span data-bind="text: params.dryad.repo"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dryad_folder_created">
created folder
<span class="overflow log-folder">{{ stripSlash(params.path) }}</span> in
dryad repo
<span data-bind="text: params.dryad.user"></span> /
<span data-bind="text: params.dryad.repo"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dryad_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
dryad repo
<span data-bind="text: params.dryad.user"></span> /
<span data-bind="text: params.dryad.repo"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dryad_file_removed">
removed file <span class="overflow" data-bind="text: params.path"></span> from
dryad repo
<span data-bind="text: params.dryad.user"></span> /
<span data-bind="text: params.dryad.repo"></span> from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dryad_repo_linked">
linked dryad repo
<span data-bind="text: params.dryad.user"></span> /
<span data-bind="text: params.dryad.repo"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dryad_repo_unlinked">
unlinked dryad repo
<span data-bind="text: params.dryad.user"></span> /
<span data-bind="text: params.dryad.repo"></span> from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dryad_node_authorized">
authorized the dryad addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dryad_node_deauthorized">
deauthorized the dryad addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dryad_node_deauthorized_no_user">
dryad addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
    deauthorized
</script>

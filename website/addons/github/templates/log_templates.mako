<script type="text/html" id="github_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> to
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_file_removed">
removed file <span class="overflow" data-bind="text: params.path"></span> from
GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> from
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_repo_linked">
selected GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> for
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_repo_unlinked">
un-selected GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> from
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

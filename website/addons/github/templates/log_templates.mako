<script type="text/html" id="github_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="if:log.anonymous">
    <span class="contributor-anonymous">a user</span>
</span>
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span>
</span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_folder_created">
created folder
<span class="overflow log-folder">{{ stripSlash(params.path) }}</span> in
GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="if:log.anonymous">
    <span class="contributor-anonymous">a user</span>
</span>
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span>
</span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="github_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="if:log.anonymous">
    <span class="contributor-anonymous">a user</span>
</span>
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span>
</span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_file_removed">
removed file <span class="overflow" data-bind="text: params.path"></span> from
GitHub repo
<span data-bind="if:log.anonymous">
    <span class="contributor-anonymous">a user</span>
</span>
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span>
</span> /
<span data-bind="text: params.github.repo"></span> from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_repo_linked">
linked GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="if:log.anonymous">
    <span class="contributor-anonymous">a user</span>
</span>
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span>
</span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_repo_unlinked">
unlinked GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="if:log.anonymous">
    <span class="contributor-anonymous">a user</span>
</span>
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span>
</span> from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_node_authorized">
authorized the GitHub addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="github_node_deauthorized">
deauthorized the GitHub addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="github_node_deauthorized_no_user">
GitHub addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
    deauthorized
</script>

<script type="text/html" id="gitlab_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
GitLab repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.gitlab.user"></span> /
</span>
<span data-bind="text: params.gitlab.repo"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="gitlab_folder_created">
created folder
<span class="overflow log-folder" data-bind="text: stripSlash(params.path)"></span> in
GitLab repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.gitlab.user"></span> /
</span>
<span data-bind="text: params.gitlab.repo"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="gitlab_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
GitLab repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.gitlab.user"></span> /
</span>
<span data-bind="text: params.gitlab.repo"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="gitlab_file_removed">
removed file <span class="overflow" data-bind="text: params.path"></span> from
GitLab repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.gitlab.user"></span> /
</span>
<span data-bind="text: params.gitlab.repo"></span> from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="gitlab_repo_linked">
linked GitLab repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.gitlab.user"></span> /
</span>
<span data-bind="text: params.gitlab.repo"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="gitlab_repo_unlinked">
unlinked GitLab repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.gitlab.user"></span> /
</span>
<span data-bind="text: params.gitlab.repo"></span> from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="gitlab_node_authorized">
authorized the GitLab addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="gitlab_node_deauthorized">
deauthorized the GitLab addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="gitlab_node_deauthorized_no_user">
GitLab addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>

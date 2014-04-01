<script type="text/html" id="gitlab_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">{{params.path}}</a> to
{{nodeCategory}}
<a class="log-node-title-link overflow" data-bind="attr.href: nodeUrl">{{nodeTitle}}</a>
</script>

<script type="text/html" id="gitlab_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">{{params.path}}</a> in
{{nodeCategory}}
<a class="log-node-title-link overflow" data-bind="attr.href: nodeUrl">{{nodeTitle}}</a>
</script>

<script type="text/html" id="gitlab_file_removed">
removed file <span class="overflow"">{{params.path}}</span> from
{{nodeCategory}}
<a class="log-node-title-link overflow" data-bind="attr.href: nodeUrl">{{nodeTitle}}</a>
</script>

<script type="text/html" id="gitlab_commit_added">
pushed commit <span class="overflow">{{params.gitlab.sha}}</span> to
{{nodeCategory}}
<a class="log-node-title-link overflow" data-bind="attr.href: nodeUrl">{{nodeTitle}}</a>
</script>

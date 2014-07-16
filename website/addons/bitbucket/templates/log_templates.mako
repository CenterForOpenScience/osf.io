<script type="text/html" id="github_file_added">
added file
<a class="overflow" data-bind="attr: {href: params.github.url}, text: params.path"></a> to
GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> in
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_file_removed">
removed file <span class="overflow" data-bind="text: params.path"></span> from
GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> in
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

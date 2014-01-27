<script type="text/html" id="s3_file_added">
added file
<a class="overflow" data-bind="attr: {href: params.s3.url, download: params.path.split('/').splice(-1)}, text: params.path"></a> to
GitHub repo
<span data-bind="text: params.s3.user"></span> /
<span data-bind="text: params.s3.repo"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_file_updated">
updated file
<a class="overflow" data-bind="attr: {href: params.s3.url, download: params.path.split('/').splice(-1)}, text: params.path"></a> to
GitHub repo
<span data-bind="text: params.s3.user"></span> /
<span data-bind="text: params.s3.repo"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_file_removed">
removed file <span class="overflow" data-bind="text: params.path"></span> from
GitHub repo
<span data-bind="text: params.s3.user"></span> /
<span data-bind="text: params.s3.repo"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

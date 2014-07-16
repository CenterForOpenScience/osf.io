<script type="text/html" id="file_added">
added file <a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="file_updated">
updated file <a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> in
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="file_removed">
removed file <span data-bind="text: params.path"></span> from
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

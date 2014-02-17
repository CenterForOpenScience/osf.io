<script type="text/html" id="file_added">
added file <a class="overflow" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="file_removed">
removed file <a class="overflow" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> from
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="file_updated">
updated file <span data-bind="text: params.path"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

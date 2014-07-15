<script type="text/html" id="figshare_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
FigShare <span data-bind="text: params.figshare.title"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="figshare_content_linked">
linked FigShare project <span data-bind="text: params.figshare.title"></span> in
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="figshare_content_unlinked">
unlinked FigShare project <span data-bind="text: params.figshare.title"></span> in
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="figshare_node_authorized">
authorized the Figshare addon for {{ nodeType }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="figshare_node_deauthorized">
deauthorized the Figshare addon for {{ nodeType }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

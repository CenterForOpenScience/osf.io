<script type="text/html" id="box_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">{{ params.path }}</a> to
Box in {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="box_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">{{ params.path }}</a> to
Box in {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="box_file_removed">
removed file <span class="overflow">{{ params.path }}</span> from
Box in {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="box_folder_selected">
linked Box folder <span class="overflow">{{ params.folder }}</span> to {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="box_node_deauthorized">
deauthorized the Box addon for {{ nodeType }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="box_node_authorized">
authorized the Box addon for {{ nodeType }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dropbox_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">{{ params.path }}</a> to
Dropbox in {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="dropbox_file_removed">
removed file <span class="overflow">{{ params.path }}</span> from
Dropbox in {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="dropbox_folder_selected">
linked Dropbox folder <span class="overflow">{{ params.folder }}</span> to {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="dropbox_node_deauthorized">
deauthorized the Dropbox addon for {{ nodeType }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="dropbox_node_authorized">
authorized the Dropbox addon for {{ nodeType }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

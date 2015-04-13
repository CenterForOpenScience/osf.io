<script type="text/html" id="googledrive_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">{{ decodeURIComponent(params.path) }}</a> to
Google Drive in {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="googledrive_folder_created">
created folder
<span class="overflow">{{ params.path }}</span> in
Google Drive in {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="googledrive_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">{{ decodeURIComponent(params.path) }}</a> to
Google Drive in {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="googledrive_file_removed">
removed {{ params.path.endsWith('/') ? 'folder' : 'file' }} <a class="overflow ">{{ params.path }}</a> from
Google Drive in {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="googledrive_folder_selected">
linked Google Drive folder /<span class="overflow">{{ params.folder === '/' ? '(Full Google Drive)' : params.folder}}</span> to {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="googledrive_node_deauthorized">
deauthorized the Google Drive addon for {{ nodeType }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="googledrive_node_authorized">
authorized the Google Drive addon for {{ nodeType }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

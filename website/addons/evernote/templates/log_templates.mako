<script type="text/html" id="evernote_folder_selected">
linked evernote folder <span class="overflow">{{ params.folder === '/' ? '/ (Full evernote)' : params.folder }}</span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="evernote_node_deauthorized">
deauthorized the evernote addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="evernote_node_authorized">
authorized the evernote addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="evernote_node_deauthorized_no_user">
evernote addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
    deauthorized
</script>

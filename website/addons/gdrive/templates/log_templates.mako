 <!-- An example log template -->
 <script type="text/html" id="gdrive_file_added">
added file

<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">{{ params.path }}</a> to
Dropbox in {{ nodeCategory }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


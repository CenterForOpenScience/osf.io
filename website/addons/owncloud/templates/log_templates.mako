<script type="text/html" id="owncloud_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.filename"></a> to
ownCloud folder <span class="overflow" data-bind="text: params.folder"></span>
in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="owncloud_file_removed">
removed file <span class="overflow" data-bind="text: params.filename"></span> from
ownCloud folder <span class="overflow" data-bind="text: params.folder"></span>
in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="owncloud_folder_linked">
linked ownCloud folder
<span class="overflow" data-bind="text: params.folder"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<!-- Legacy version -->
<script type="text/html" id="owncloud_study_linked">
linked ownCloud folder
<span class="overflow" data-bind="text: params.study"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="owncloud_folder_published">
published a new version of ownCloud folder
<span class="overflow" data-bind="text: params.folder"></span> to
for
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<!-- Legacy version -->
<script type="text/html" id="owncloud_study_released">
published a new version of ownCloud folder
<span class="overflow" data-bind="text: params.study"></span> to
for
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="owncloud_node_authorized">
authorized the ownCloud addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="owncloud_node_deauthorized">
deauthorized the ownCloud addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="owncloud_node_deauthorized_no_user">
ownCloud addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>

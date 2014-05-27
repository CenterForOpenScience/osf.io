<script type="text/html" id="dataverse_file_added">
added file
<a class="overflow log-file-link" data-bind="attr: {href: params.path}, text: params.filename"></a> to
Dataverse study
<span data-bind="text: params.dataverse.dataverse"></span> /
<span data-bind="text: params.dataverse.study"></span> to
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dataverse_file_removed">
removed file <span class="overflow">{{ params.filename }}</span> from
Dataverse study
<span>{{ params.dataverse.dataverse }}</span> /
<span data-bind="text: params.dataverse.study"></span> from
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dataverse_study_linked">
selected Dataverse study
<span data-bind="text: params.dataverse.dataverse"></span> /
<span data-bind="text: params.dataverse.study"></span> for
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dataverse_study_unlinked">
un-selected Dataverse study
<span data-bind="text: params.dataverse.dataverse"></span> /
<span data-bind="text: params.dataverse.study"></span> from
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dataverse_study_released">
released a new version of Dataverse study
<span data-bind="text: params.dataverse.dataverse"></span> /
<span data-bind="text: params.dataverse.study"></span> for
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dataverse_node_deauthorized">
deauthorized the Dataverse addon for {{ nodeCategory }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="dataverse_node_authorized">
authorized the Dataverse addon for {{ nodeCategory }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>
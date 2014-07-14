<script type="text/html" id="dataverse_file_added">
added file
<a class="overflow log-file-link" data-bind="attr: {href: params.path}, text: params.filename"></a> to
Dataverse study <span class="overflow">{{ params.study }}</span>
in {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dataverse_file_removed">
removed file <span class="overflow">{{ params.filename }}</span> from
Dataverse study <span class="overflow">{{ params.study }}</span>
in {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dataverse_study_linked">
linked Dataverse study
<span class="overflow">{{ params.study }}</span> to {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dataverse_study_released">
released a new version of Dataverse study
<span class="overflow">{{ params.study }}</span> to {{ nodeType }}
for {{ nodeType }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dataverse_node_authorized">
authorized the Dataverse addon for {{ nodeType }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dataverse_node_deauthorized">
deauthorized the Dataverse addon for {{ nodeType }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

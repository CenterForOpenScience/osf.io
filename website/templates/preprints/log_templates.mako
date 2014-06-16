<script type="text/html" id="project_created">
created <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="created_from">
created <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a> based on <a class="log-node-title-link overflow" data-bind="attr: {href: params.template_node.url}">another <span data-bind="text: nodeCategory"></span></a>
</script>

<script type="text/html" id="node_created">
created <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="node_removed">
removed <span data-bind="text: nodeCategory"></span>
<span class="overflow" data-bind="text: nodeTitle"></span>
</script>

<script type="text/html" id="wiki_updated">
updated wiki page
<a data-bind="attr: {href: wikiUrl}, text: params.page"></a>
to version <span data-bind="text: params.version"></span>
</script>

<script type="text/html" id="contributor_added">
added
<span data-bind="html: displayContributors"></span>
to <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="contributor_removed">
removed
<span data-bind="html: displayContributors"></span>
as contributor(s) from
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="contributors_reordered">
reordered contributors for
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="permissions_updated">
changed permissions for
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="made_public">
made <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> public
</script>

<script type="text/html" id="made_private">
made <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> private
</script>

<script type="text/html" id="tag_added">
tagged
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> as <a data-bind="attr: {href: '/tags/' + params.tag + '/'}, text: params.tag"></a>
</script>

<script type="text/html" id="tag_removed">
removed tag <a data-bind="attr: {href: '/tags/' + params.tag + '/'}, text: params.tag"></a>
from <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="edit_title">
changed the title from <span class="overflow" data-bind="text: params.title_original"></span>
to <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: params.title_new"></a>
</script>

<script type="text/html" id="project_registered">
registered <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="node_forked">
created fork from <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="edit_description">
edited description of <span data-bind="text: nodeCategory"></span> <a class="log-node-title-link" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="pointer_created">
created a link to <span data-bind="text: params.pointer.category"></span>
<a class="log-node-title-link overflow" data-bind="text: params.pointer.title, attr: {href: params.pointer.url}"></a>
</script>

<script type="text/html" id="pointer_removed">
removed a link to <span data-bind="text: params.pointer.category"></span>
<a class="log-node-title-link overflow" data-bind="text: params.pointer.title, attr: {href: params.pointer.url}"></a>
</script>

<script type="text/html" id="pointer_forked">
forked a link to <span data-bind="text: params.pointer.category"></span>
<a class="log-node-title-link overflow" data-bind="text: params.pointer.title, attr: {href: params.pointer.url}"></a>
</script>

<script type="text/html" id="addon_added">
added addon <span data-bind="text: params.addon"></span>
to <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="addon_removed">
removed addon <span data-bind="text: params.addon"></span>
from <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_added">
added a comment
to <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_updated">
updated a comment
on <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_removed">
deleted a comment
on <span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>
<script type="text/html" id="file_added">
added file <a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="file_updated">
updated file <a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="file_removed">
removed file <span data-bind="text: params.path"></span> from
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>
<script type="text/html" id="github_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> to
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_file_removed">
removed file <span class="overflow" data-bind="text: params.path"></span> from
GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> from
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_repo_linked">
selected GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> for
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_repo_unlinked">
un-selected GitHub repo
<span data-bind="text: params.github.user"></span> /
<span data-bind="text: params.github.repo"></span> from
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>
<script type="text/html" id="s3_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
bucket
<span data-bind="text: params.bucket"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path}"></a> in
bucket
<span data-bind="text: params.bucket"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_file_removed">
removed file <span class="overflow" data-bind="text: params.path"></span> from
bucket
<span data-bind="text: params.bucket"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_bucket_linked">
selected bucket
<span data-bind="text: params.bucket"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_bucket_unlinked">
un-selected bucket
<span data-bind="text: params.bucket"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>
<script type="text/html" id="figshare_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
FigShare <span data-bind="text: params.figshare.title"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="figshare_content_linked">
linked FigShare project <span data-bind="text: params.figshare.title"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="figshare_content_unlinked">
unlinked FigShare project <span data-bind="text: params.figshare.title"></span> in
<span data-bind="text: nodeCategory"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>
<script type="text/html" id="dropbox_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect">{{ params.path }}</a> to
Dropbox in {{ nodeCategory }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="dropbox_file_removed">
removed file <span class="overflow">{{ params.path }}</span> from
Dropbox in {{ nodeCategory }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="dropbox_folder_selected">
linked Dropbox folder <span class="overflow">{{ params.folder }}</span> to {{ nodeCategory }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="dropbox_node_deauthorized">
deauthorized the Dropbox addon for {{ nodeCategory }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>


<script type="text/html" id="dropbox_node_authorized">
authorized the Dropbox addon for {{ nodeCategory }}
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>
<script type="text/html" id="dataverse_file_added">
added file
<a class="overflow log-file-link" data-bind="attr: {href: params.path}, text: params.filename"></a> to
Dataverse study <span class="overflow">{{ params.study }}</span>
in {{ nodeCategory }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dataverse_file_removed">
removed file <span class="overflow">{{ params.filename }}</span> from
Dataverse study <span class="overflow">{{ params.study }}</span>
in {{ nodeCategory }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dataverse_study_linked">
linked Dataverse study
<span class="overflow">{{ params.study }}</span> to {{ nodeCategory }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
</script>

<script type="text/html" id="dataverse_study_released">
released a new version of Dataverse study
<span class="overflow">{{ params.study }}</span> to {{ nodeCategory }}
for {{ nodeCategory }}
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ nodeTitle }}</a>
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
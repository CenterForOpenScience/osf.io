## Knockout templates for OSF-core (non-addon) logs. Used by logFeed.js to render the log feed
## the id attribute of each script tag corresponds to NodeLog action.
## When the application is initialized, this mako template is concatenated with the addons'
## log templates. An addon's log templates are located in
## website/addons/<addon_name>/templates/log_templates.mako.

<script type="text/html" id="project_created">
created <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="project_deleted">
deleted <span data-bind="text: nodeType"></span>
<span class="log-node-title-link overflow" data-bind="text: nodeTitle"></span>
</script>

<script type="text/html" id="created_from">
created <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a> based on <a class="log-node-title-link overflow" data-bind="attr: {href: params.template_node.url}">another <span data-bind="text: nodeType"></span></a>
</script>

<script type="text/html" id="node_created">
created <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="node_removed">
removed <span data-bind="text: nodeType"></span>
<span class="log-node-title-link overflow" data-bind="text: nodeTitle"></span>
</script>

<script type="text/html" id="contributor_added">
added
<span data-bind="html: displayContributors"></span>
as contributor(s) to
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="contributor_removed">
removed
<span data-bind="html: displayContributors"></span>
as contributor(s) from
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="contributors_reordered">
reordered contributors for
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="permissions_updated">
changed permissions for
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="made_public">
made <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> public
</script>

<script type="text/html" id="made_private">
made <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> private
</script>

<script type="text/html" id="tag_added">
tagged
<span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> as <a class='tag' data-bind="attr: {href: '/search/?q=%22' + params.tag + '%22'}, text: params.tag"></a>
</script>

<script type="text/html" id="tag_removed">
removed tag <a class='tag' data-bind="attr: {href: '/search/?q=%22' + params.tag + '%22'}, text: params.tag"></a>
from <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="edit_title">
changed the title from <span class="overflow" data-bind="text: params.title_original"></span>
to <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: params.title_new"></a>
</script>

<script type="text/html" id="project_registered">
registered <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="node_forked">
created fork from <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="edit_description">
edited description of <span data-bind="text: nodeType"></span> <a class="log-node-title-link" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
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
to <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="addon_removed">
removed addon <span data-bind="text: params.addon"></span>
from <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_added">
added a comment
to <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_updated">
updated a comment
on <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_removed">
deleted a comment
on <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="made_contributor_visible">
made contributor
<span data-bind="html: displayContributors"></span>
visible on <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="made_contributor_invisible">
made contributor
<span data-bind="html: displayContributors"></span>
invisible on <span data-bind="text: nodeType"></span>
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

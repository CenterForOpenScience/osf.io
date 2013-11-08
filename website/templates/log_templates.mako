<script type="text/html" id="project_created">
created <span data-bind="text: nodeCategory"></span>
<a data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="node_created">
created <span data-bind="text: nodeCategory"></span>
<a data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
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
  <a data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="contributor_removed">
removed <a data-bind="attr: {href: '/profile/' + contributor.id + '/'}, text: contributor.fullname"></a> as a contributor from
<span data-bind="text: nodeCategory"></span>
<a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="made_public">
made <span data-bind="text: nodeCategory"></span>
<a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> public
</script>

<script type="text/html" id="made_private">
made <span data-bind="text: nodeCategory"></span>
<a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> private
</script>

<script type="text/html" id="tag_added">
tagged
<span data-bind="text: nodeCategory"></span>
<a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> as <a data-bind="attr: {href: '/tags/' + params.tag + '/'}, text: params.tag"></a>
</script>

<script type="text/html" id="tag_removed">
removed tag <a data-bind="attr: {href: '/tags/' + params.tag + '/'}, text: params.tag"></a>
from <span data-bind="text: nodeCategory"></span>
<a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="edit_title">
changed the title from <span data-bind="text: params.title_original"></span>
to <span data-bind="text: nodeCategory"></span>
<a data-bind="attr: {href: nodeUrl}, text: params.title_new"></a>
</script>

<script type="text/html" id="project_registered">
registered <span data-bind="text: nodeCategory"></span>
<a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="file_added">
added file <span data-bind="text: params.path"></span> to
<span data-bind="text: nodeCategory"></span>
<a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="file_removed">
removed file <span data-bind="text: params.path"></span> from
<span data-bind="text: nodeCategory"></span>
<a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="file_updated">
updated file <span data-bind="text: params.path"></span> in
<span data-bind="text: nodeCategory"></span>
<a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="node_forked">
created fork from <span data-bind="text: nodeCategory"></span>
<a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

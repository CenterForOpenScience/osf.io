## Knockout templates for OSF-core (non-addon) logs. Used by logFeed.js to render the log feed
## the id attribute of each script tag corresponds to NodeLog action.
## When the application is initialized, this mako template is concatenated with the addons'
## log templates. An addon's log templates are located in
## website/addons/<addon_name>/templates/log_templates.mako.

## Embargo related logs
<script type="text/html" id="embargo_approved">
approved embargoed registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: projectUrl}"></a>
</script>

<script type="text/html" id="embargo_approved_no_user">
Embargo for
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a> approved
</script>

<script type="text/html" id="embargo_cancelled">
cancelled embargoed registration of
<span class="log-node-title-link overflow" data-bind="text: nodeTitle"></span>
</script>

<script type="text/html" id="embargo_completed">
completed embargo of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="embargo_completed_no_user">
Embargo for
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a> completed
</script>

<script type="text/html" id="embargo_initiated">
initiated an embargoed registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: projectUrl}"></a>
</script>

## Retraction related logs
<script type="text/html" id="retraction_approved">
approved retraction of registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: projectUrl}"></a>
</script>

<script type="text/html" id="retraction_cancelled">
cancelled retraction of registration of
<span class="log-node-title-link overflow" data-bind="text: nodeTitle"></span>
</script>

<script type="text/html" id="retraction_initiated">
initiated retraction of registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: projectUrl}"></a>
</script>

## Registration related Logs
<script type="text/html" id="registration_initiated">
initiated registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: projectUrl}"></a>
</script>

<script type="text/html" id="registration_cancelled">
cancelled registration of
<span class="log-node-title-link overflow" data-bind="text: nodeTitle"></span>
</script>

<script type="text/html" id="registration_approved">
approved registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle , attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="registration_approved_no_user">
Registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a> approved
</script>

## Project related logs
<script type="text/html" id="project_created">
created
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="project_deleted">
deleted
<span class="log-node-title-link overflow" data-bind="text: nodeTitle"></span>
</script>

<script type="text/html" id="created_from">
created
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
based on <a class="log-node-title-link overflow"
data-bind="text: params.template_node.title || 'another', attr: {href: params.template_node.url}"></a>
</script>

<script type="text/html" id="node_created">
created
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="node_removed">
removed
<span class="log-node-title-link overflow" data-bind="text: nodeTitle"></span>
</script>

<script type="text/html" id="contributor_added">
added
<span data-bind="html: displayContributors"></span>
as contributor(s) to
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="contributor_removed">
removed
<span data-bind="html: displayContributors"></span>
as contributor(s) from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="contributors_reordered">
reordered contributors for
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="permissions_updated">
changed permissions for
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="made_public">
made
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> public
</script>

<script type="text/html" id="made_public_no_user">
    <a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> made public
</script>

<script type="text/html" id="made_private">
made
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> private
</script>

<script type="text/html" id="tag_added">
tagged
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> as <a data-bind="attr: {href: '/search/?q=%22' + params.tag + '%22'}, text: params.tag"></a>
</script>

<script type="text/html" id="tag_removed">
removed tag <a data-bind="attr: {href: '/search/?q=%22' + params.tag + '%22'}, text: params.tag"></a>
from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="edit_title">
changed the title from <span class="overflow" data-bind="text: params.title_original"></span>
to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}">{{ params.title_new }}</a>
</script>

<script type="text/html" id="project_registered">
registered
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="project_registered_no_user">
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> registered
</script>

<script type="text/html" id="node_forked">
created fork from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="edit_description">
edited description of  <a class="log-node-title-link" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="license_changed">
updated the license of <a class="log-node-title-link" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="updated_fields">
  changed the <span data-bind="listing: {
                                 data: params.updated_fields,
                                 map: mapUpdates
                               }"></span> for
  <a class="log-node-title-link" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
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
to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="addon_removed">
removed addon <span data-bind="text: params.addon"></span>
from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_added">
added a comment
to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_updated">
updated a comment
on
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_removed">
deleted a comment
on
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="made_contributor_visible">
made contributor
<span data-bind="html: displayContributors"></span>
visible on
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="made_contributor_invisible">
made contributor
<span data-bind="html: displayContributors"></span>
invisible on
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="addon_file_copied">
  {{#if params.source.materialized.endsWith('/')}}
    copied <span class="overflow log-folder">{{ params.source.materialized }}</span> from {{ params.source.addon }} in
    <a class="log-node-title-link overflow" href="{{ params.source.node.url }}">{{ params.source.node.title }}</a>
    to <span class="overflow log-folder">{{ params.destination.materialized }}</span> in {{ params.destination.addon }} in
    <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
  {{/if}}
  {{#ifnot params.source.materialized.endsWith('/')}}
    copied <a href="{{ params.source.url }}" class="overflow">{{ params.source.materialized }}</a> from {{ params.source.addon }} in
    <a class="log-node-title-link overflow" href="{{ params.source.node.url }}">{{ params.source.node.title }}</a>
    to <a href="{{ params.destination.url }}" class="overflow">{{ params.destination.materialized }}</a> in {{ params.destination.addon }} in
    <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
  {{/ifnot}}
</script>

<script type="text/html" id="addon_file_moved">
  {{#if params.source.materialized.endsWith('/')}}
  moved <span class="overflow">{{ params.source.materialized }}</span> from {{ params.source.addon }} in
  <a class="log-node-title-link overflow" href="{{ params.source.node.url }}">{{ params.source.node.title }}</a>
  to <span class="overflow log-folder">{{ params.destination.materialized }}</span> in {{ params.destination.addon }} in
  <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
  {{/if}}
  {{#ifnot params.source.materialized.endsWith('/')}}
  moved <span class="overflow">{{ params.source.materialized }}</span> from {{ params.source.addon }} in
  <a class="log-node-title-link overflow" href="{{ params.source.node.url }}">{{ params.source.node.title }}</a>
  to <a href="{{ params.destination.url }}" class="overflow">{{ params.destination.materialized }}</a> in {{ params.destination.addon }} in
  <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
  {{/ifnot}}
</script>

<script type="text/html" id="addon_file_renamed">
    renamed <span class="overflow">{{ params.source.materialized }}</span>
  {{#if params.source.materialized.endsWith('/')}}
  to <span class="overflow log-folder">{{ params.destination.materialized }}</span> in {{ params.destination.addon }} in
  {{/if}}
  {{#ifnot params.source.materialized.endsWith('/')}}
  to <a href="{{ params.destination.url }}" class="overflow">{{ params.destination.materialized }}</a> in {{ params.destination.addon }} in
  {{/ifnot}}
    <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="external_ids_added">
created external identifiers
<span data-bind="text: 'doi:' + params.identifiers.doi"></span> and
<span data-bind="text: 'ark:' + params.identifiers.ark"></span>
on
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

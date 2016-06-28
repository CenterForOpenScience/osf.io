## Built templates file. DO NOT MODIFY.

<script type="text/html" id="embargo_approved">
approved embargoed registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="embargo_approved_no_user">
Embargo of registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a> approved
</script>

<script type="text/html" id="embargo_cancelled">
cancelled embargoed registration of
<span class="log-node-title-link overflow" data-bind="text: nodeTitle"></span>
</script>

<script type="text/html" id="embargo_completed_no_user">
Embargo of registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a> completed
</script>

<script type="text/html" id="embargo_initiated">
initiated an embargoed registration of
<!-- ko if: !registrationCancelled -->
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
<!-- /ko -->

<!-- ko if: registrationCancelled -->
<span class="log-node-title-link overflow" data-bind="text: nodeTitle"></span>
<!-- /ko -->
</script>

<script type="text/html" id="embargo_terminated_no_user">
Embargo for
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
ended
</script>

<script type="text/html" id="retraction_approved">
approved withdrawal of registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="retraction_cancelled">
cancelled withdrawal of registration of
<span class="log-node-title-link overflow" data-bind="text: nodeTitle"></span>
</script>

<script type="text/html" id="retraction_initiated">
initiated withdrawal of registration of
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="registration_initiated">
initiated registration of
<!-- ko if: !registrationCancelled -->
<a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>
<!-- /ko -->

<!-- ko if: registrationCancelled -->
<span class="log-node-title-link overflow" data-bind="text: nodeTitle"></span>
<!-- /ko -->
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

<script type="text/html" id="checked_in">
checked in <span data-bind="text: params.kind"></span>
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: stripSlash(params.path)"></a>
from <a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="checked_out">
checked out <span data-bind="text: params.kind"></span>
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: stripSlash(params.path)"></a>
from
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

<script type="text/html" id="file_tag_added">
tagged <a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: stripSlash(params.path)"></a>
in <a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
as <a data-bind="attr: {href: '/search/?q=%22' + params.tag + '%22'}, text: params.tag"></a>
in OSF Storage
</script>

<script type="text/html" id="file_tag_removed">
removed tag <a data-bind="attr: {href: '/search/?q=%22' + params.tag + '%22'}, text: params.tag"></a>
from <a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: stripSlash(params.path)"></a>
in <a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
in OSF Storage
</script>

<script type="text/html" id="edit_title">
changed the title from <span class="overflow" data-bind="text: params.title_original"></span>
to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: params.title_new"></a>
</script>

<script type="text/html" id="project_registered">
        registered
        <a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="prereg_registration_initiated">
    submitted for review to the Preregistration Challenge a registration of
    <a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>.
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
<!-- ko if: params.file -->
<a data-bind="attr: {href: params.file.url}, text: params.file.name"></a>
in
<!-- /ko -->
<!-- ko if: params.wiki -->
wiki page
<a data-bind="attr: {href: params.wiki.url}, text: params.wiki.name"></a>
in
<!-- /ko -->
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_updated">
updated a comment
on
<!-- ko if: params.file -->
<a data-bind="attr: {href: params.file.url}, text: params.file.name"></a>
in
<!-- /ko -->
<!-- ko if: params.wiki -->
wiki page
<a data-bind="attr: {href: params.wiki.url}, text: params.wiki.name"></a>
in
<!-- /ko -->
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_removed">
deleted a comment
on
<!-- ko if: params.file -->
<a data-bind="attr: {href: params.file.url}, text: params.file.name"></a>
in
<!-- /ko -->
<!-- ko if: params.wiki -->
wiki page
<a data-bind="attr: {href: params.wiki.url}, text: params.wiki.name"></a>
in
<!-- /ko -->
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="comment_restored">
restored a comment
on
<!-- ko if: params.file -->
<a data-bind="attr: {href: params.file.url}, text: params.file.name"></a>
in
<!-- /ko -->
<!-- ko if: params.wiki -->
wiki page
<a data-bind="attr: {href: params.wiki.url}, text: params.wiki.name"></a>
in
<!-- /ko -->
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="made_contributor_visible">
    <!-- ko if: log.anonymous -->
        changed a non-bibliographic contributor to a bibliographic contributor on
    <!-- /ko -->
    <!-- ko ifnot: log.anonymous -->
        made non-bibliographic contributor
        <span data-bind="html: displayContributors"></span>
        a bibliographic contributor on
    <!-- /ko -->
    <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="made_contributor_invisible">
    <!-- ko if: log.anonymous -->
        changed a bibliographic contributor to a non-bibliographic contributor on
    <!-- /ko -->
    <!-- ko ifnot: log.anonymous -->
        made bibliographic contributor
        <span data-bind="html: displayContributors"></span>
        a non-bibliographic contributor on
    <!-- /ko -->
    <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="addon_file_copied">
  <!-- ko if: params.source.materialized.endsWith('/') -->
    copied <span class="overflow log-folder" data-bind="text: params.source.materialized"></span> from <span data-bind="text: params.source.addon"></span> in
    <a class="log-node-title-link overflow" data-bind="attr: {href: params.source.node.url}, text:params.source.node.title"></a>
    to <span class="overflow log-folder" data-bind="text: params.destination.materialized"></span> in <span data-bind="text: params.destination.addon"></span> in
    <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
  <!-- /ko -->
  <!-- ko ifnot: params.source.materialized.endsWith('/') -->
    copied <a data-bind="attr: {href: params.source.url}, text: params.source.materialized" class="overflow"></a> from <span data-bind="text: params.source.addon"></span> in
    <a class="log-node-title-link overflow" data-bind="attr: {href: params.source.node.url}, text: params.source.node.title"></a>
    to <a data-bind="attr: {href: params.destination.url}, text: params.destination.materialized" class="overflow"></a> in <span data-bind="text: params.destination.addon"></span> in
    <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
  <!-- /ko -->
</script>

<script type="text/html" id="addon_file_moved">
  <!-- ko if: params.source.materialized.endsWith('/') -->
  moved <span class="overflow" data-bind="text: params.source.materialized"></span> from <span data-bind="text: params.source.addon"></span> in
  <a class="log-node-title-link overflow" data-bind="attr: {href: params.source.node.url}, text: params.source.node.title"></a>
  to <span class="overflow log-folder" data-bind="text: params.destination.materialized"></span> in <span data-bind="text: params.destination.addon"></span> in
  <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
  <!-- /ko -->
  <!-- ko ifnot: params.source.materialized.endsWith('/') -->
  moved <span class="overflow" data-bind="text: params.source.materialized"></span> from <span data-bind="text: params.source.addon"></span> in
  <a class="log-node-title-link overflow" data-bind="attr: {href: params.source.node.url}, text: params.source.node.title"></a>
  to <a class="overflow" data-bind="attr: {href: params.destination.url}, text: params.destination.materialized"></a> in <span data-bind="text: params.destination.addon"></span> in
  <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
  <!-- /ko -->
</script>

<script type="text/html" id="addon_file_renamed">
    renamed <span class="overflow" data-bind="text: params.source.materialized"></span>
  <!-- ko if: params.source.materialized.endsWith('/') -->
  to <span class="overflow log-folder" data-bind="text: params.destination.materialized"></span> in <span data-bind="text: params.destination.addon"></span> in
  <!-- /ko -->
  <!-- ko ifnot: params.source.materialized.endsWith('/') -->
  to <a class="overflow" data-bind="attr: {href: params.destination.url}, text: params.destination.materialized"></a> in <span data-bind="text: params.destination.addon"></span>  in
  <!-- /ko -->
    <a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="external_ids_added">
created external identifiers
<span data-bind="text: 'doi:' + params.identifiers.doi"></span> and
<span data-bind="text: 'ark:' + params.identifiers.ark"></span>
on
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="citation_added">
added a citation (<span data-bind="text: params.citation.name"></span>)
to
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="citation_edited">
<!-- ko if: params.citation.new_name -->
updated a citation name from <span data-bind="text: params.citation.name"></span> to <strong data-bind="text: params.citation.new_name"></strong>
  <!-- ko if: params.citation.new_text -->
    and edited its text
  <!-- /ko -->
<!-- /ko -->
<!-- ko ifnot: params.citation.new_name -->
edited the text of a citation (<span data-bind="text: params.citation.name"></span>)
<!-- /ko -->
on
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="citation_removed">
removed a citation (<span data-bind="text: params.citation.name"></span>)
from
<a class="log-node-title-link overflow" data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
</script>

<script type="text/html" id="affiliated_institution_added">
added <a class="log-node-title-link overflow" data-bind="attr: {href: '/institutions/' + params.institution.id}, text: params.institution.name"></a>
 affiliation to <a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>.
</script>

<script type="text/html" id="affiliated_institution_removed">
removed <a class="log-node-title-link overflow" data-bind="attr: {href: '/institutions/' + params.institution.id}, text: params.institution.name"></a>
 affiliation from <a class="log-node-title-link overflow" data-bind="text: nodeTitle, attr: {href: nodeUrl}"></a>.
</script>
<script type="text/html" id="box_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: stripSlash(params.path)"></a> to
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="box_folder_created">
created folder
<span class="overflow log-folder" data-bind="text: stripSlash(params.path)"></span> in
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="box_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: stripSlash(params.path)"></a> to
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="box_file_removed">
removed <span data-bind="text: pathType(params.path) "></span> <span class="overflow" data-bind="text: stripSlash(params.path)"></span> from
Box in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="box_folder_selected">
linked Box folder
<span class="overflow" data-bind="text: (params.folder === 'All Files' ? '/ (Full Box)' : (params.folder || '').replace('All Files',''))"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="box_node_deauthorized">
deauthorized the Box addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="box_node_authorized">
authorized the Box addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="box_node_deauthorized_no_user">
Box addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>
<script type="text/html" id="dataverse_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.filename"></a> to
Dataverse dataset <span class="overflow" data-bind="text: params.dataset"></span>
in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dataverse_file_removed">
removed file <span class="overflow" data-bind="text: params.filename"></span> from
Dataverse dataset <span class="overflow" data-bind="text: params.dataset"></span>
in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dataverse_dataset_linked">
linked Dataverse dataset
<span class="overflow" data-bind="text: params.dataset"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<!-- Legacy version -->
<script type="text/html" id="dataverse_study_linked">
linked Dataverse dataset
<span class="overflow" data-bind="text: params.study"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dataverse_dataset_published">
published a new version of Dataverse dataset
<span class="overflow" data-bind="text: params.dataset"></span> to
for
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<!-- Legacy version -->
<script type="text/html" id="dataverse_study_released">
published a new version of Dataverse dataset
<span class="overflow" data-bind="text: params.study"></span> to
for
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dataverse_node_authorized">
authorized the Dataverse addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dataverse_node_deauthorized">
deauthorized the Dataverse addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dataverse_node_deauthorized_no_user">
Dataverse addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>
<script type="text/html" id="dropbox_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
Dropbox in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dropbox_folder_created">
created folder
<span class="overflow log-folder" data-bind="text: stripSlash(params.path)"></span> in
Dropbox in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dropbox_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
Dropbox in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="dropbox_file_removed">
removed <span data-bind="text: pathType(params.path)"></span> <span class="overflow" data-bind="text: stripSlash(params.path)"></span> from
Dropbox in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="dropbox_folder_selected">
linked Dropbox folder <span class="overflow" data-bind="text: params.folder === '/' ? '/ (Full Dropbox)' : params.folder"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="dropbox_node_deauthorized">
deauthorized the Dropbox addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="dropbox_node_authorized">
authorized the Dropbox addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="dropbox_node_deauthorized_no_user">
Dropbox addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>
<script type="text/html" id="figshare_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
figshare <span data-bind="text: params.figshare.title"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="figshare_file_removed">
removed file <span class="overflow" data-bind="text: params.path"></span> from
figshare in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="figshare_content_linked">
linked figshare project /<span data-bind="text: params.figshare.title"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="figshare_content_unlinked">
unlinked figshare project /<span data-bind="text: params.figshare.title"></span> from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="figshare_node_authorized">
authorized the figshare addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="figshare_node_deauthorized">
deauthorized the figshare addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="figshare_node_deauthorized_no_user">
figshare addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>
<script type="text/html" id="forward_url_changed">
changed forward URL to
<a class="overflow log-file-link" data-bind="attr: {href: params.forward_url}, text: params.forward_url"></a>
in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>
<script type="text/html" id="github_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
GitHub repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span> /
</span>
<span data-bind="text: params.github.repo"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_folder_created">
created folder
<span class="overflow log-folder" data-bind="text: stripSlash(params.path)"></span> in
GitHub repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span> /
</span>
<span data-bind="text: params.github.repo"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
GitHub repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span> /
</span>
<span data-bind="text: params.github.repo"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_file_removed">
removed file <span class="overflow" data-bind="text: params.path"></span> from
GitHub repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span> /
</span>
<span data-bind="text: params.github.repo"></span> from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_repo_linked">
linked GitHub repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span> /
</span>
<span data-bind="text: params.github.repo"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_repo_unlinked">
unlinked GitHub repo
<span data-bind="ifnot:log.anonymous">
    <span data-bind="text: params.github.user"></span> /
</span>
<span data-bind="text: params.github.repo"></span> from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_node_authorized">
authorized the GitHub addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_node_deauthorized">
deauthorized the GitHub addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="github_node_deauthorized_no_user">
GitHub addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>


<script type="text/html" id="mendeley_folder_selected">
linked Mendeley folder /<span class="overflow" data-bind="text: params.folder_name"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="mendeley_node_deauthorized">
deauthorized the Mendeley addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="mendeley_node_authorized">
authorized the Mendeley addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>
<script type="text/html" id="zotero_folder_selected">
linked Zotero folder /<span class="overflow" data-bind="text: params.folder_name"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="zotero_node_deauthorized">
deauthorized the Zotero addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="zotero_node_authorized">
authorized the Zotero addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>
<script type="text/html" id="osf_storage_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: stripSlash(params.path)"></a> to OSF Storage in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="osf_storage_folder_created">
created folder
<span class="overflow log-folder" data-bind="text: stripSlash(params.path)"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="osf_storage_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: stripSlash(params.path)"></a> to OSF Storage in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="osf_storage_file_removed">
  removed <span data-bind="text: pathType(params.path)"></span> <span class="overflow" data-bind="text: stripSlash(params.path)"></span>
  from OSF Storage in
  <a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


## Legacy log templates for previous OSF Files
<script type="text/html" id="file_added">
added file <a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="file_updated">
updated file <a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="file_removed">
removed file <span data-bind="text: params.path"></span> from
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>
<script type="text/html" id="s3_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> to
bucket
<span data-bind="text: params.bucket"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_folder_created">
created folder
<span class="overflow log-folder" data-bind="text: stripSlash(params.path)"></span> in
bucket <span data-bind="text: params.bucket"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: params.path"></a> in
bucket
<span data-bind="text: params.bucket"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_file_removed">
removed <span data-bind="text: pathType(params.path)"></span> <span class="overflow" data-bind="text: stripSlash(params.path)"></span> from
bucket
<span data-bind="text: params.bucket"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_bucket_linked">
linked the Amazon S3 bucket /
<span data-bind="text: params.bucket"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_bucket_unlinked">
un-selected bucket
<span data-bind="text: params.bucket"></span> in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_node_authorized">
authorized the Amazon S3 addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_node_deauthorized">
deauthorized the Amazon S3 addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="s3_node_deauthorized_no_user">
Amazon S3 addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>
<script type="text/html" id="wiki_updated">
updated wiki page
<a data-bind="attr: {href: wikiUrl}, text: params.page"></a>
to version <span data-bind="text: params.version"></span>
of <a class = "log-node-title-link overflow" data-bind="text:nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="wiki_renamed">
renamed wiki page
<a data-bind="attr: {href: wikiIdUrl}, text: params.old_page"></a>
to <a data-bind="attr: {href: wikiIdUrl}, text: params.page"></a>
of <a class = "log-node-title-link overflow" data-bind="text:nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="wiki_deleted">
deleted wiki page
<a data-bind="attr: {href: wikiUrl}, text: params.page"></a>
of <a class = "log-node-title-link overflow" data-bind="text:nodeTitle, attr: {href: nodeUrl}"></a>
</script>

<script type="text/html" id="made_wiki_public">
made the wiki
of <a class = "log-node-title-link overflow" data-bind="text:nodeTitle, attr: {href: nodeUrl}"></a>
publicly editable
</script>

<script type="text/html" id="made_wiki_private">
made the wiki
of <a class = "log-node-title-link overflow" data-bind="text:nodeTitle, attr: {href: nodeUrl}"></a>
privately editable
</script>
<script type="text/html" id="googledrive_file_added">
added file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: decodeURIComponent(params.path)"></a> to
Google Drive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="googledrive_folder_created">
created folder
<span class="overflow log-folder" data-bind="text: stripSlash(decodeURIComponent(params.path))"></span> in
Google Drive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="googledrive_file_updated">
updated file
<a class="overflow log-file-link" data-bind="click: NodeActions.addonFileRedirect, text: decodeURIComponent(params.path)"></a> to
Google Drive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="googledrive_file_removed">
removed <span data-bind="text: pathType(params.path) "></span> <span class="overflow" data-bind="text: stripSlash(decodeURIComponent(params.path))"></span> from
Google Drive in
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="googledrive_folder_selected">
linked Google Drive folder /<span class="overflow" data-bind="text: (params.folder === '/' ? '(Full Google Drive)' : decodeURIComponent(params.folder))"></span> to
<a class="log-node-title-link overflow" data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>


<script type="text/html" id="googledrive_node_deauthorized">
deauthorized the Google Drive addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="googledrive_node_deauthorized">
Google Drive addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>


<script type="text/html" id="googledrive_node_authorized">
authorized the Google Drive addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
</script>

<script type="text/html" id="googledrive_node_deauthorized_no_user">
Google Drive addon for
<a class="log-node-title-link overflow"
    data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    deauthorized
</script>

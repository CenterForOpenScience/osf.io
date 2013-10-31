<script type="text/html" id="logTemplate">
  <dt><span class="date" data-bind="text: date"></span></dt>
  <dd>
    <span data-bind="text: userFullName || apiKey"></span>

    <span data-bind="visible: action === 'project_created' || action === 'node_created'">
      created <a data-bind="text: nodeCategory, attr: {href: nodeUrl}"></a>
    </span>

    <span data-bind="visible: action === 'wiki_updated'">updated wiki page <a data-bind="attr: {href: wikiUrl}, text: params.page"></a>
    </span>

    <span data-bind="visible: action === 'contributor_added', foreach: {data: contributors, as: 'person'}">
      added <a data-bind="attr: {href: '/profile/' + person.id + '/'}, text: person.fullname"></a>
      <span data-bind="visible: $index != $parent.contributors.length"></span>

      to <a data-bind="attr: {href: $parent.nodeUrl}, text: $parent.nodeTitle"></a>
    </span><!-- end foreach contributor -->

    <span data-bind="visible: action === 'contributor_removed'">
      removed <a data-bind="attr: {href: '/profile/' + contributor.id + '/'}, text: contributor.fullname"></a> as a contributor from <a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a></a>
    </span>

    <span data-bind="visible: action === 'made_public'">
    made <a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> public
    </span>

    <span data-bind="visible: action === 'made_private'">
    made <a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> private
    </span>

    <span data-bind="visible: action === 'tag_added'">
      tagged <a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a> as <a data-bind="attr: {href: '/tags/' + params.tag + '/'}, text: params.tag"></a>
    </span>

    <span data-bind="visible: action === 'tag_removed'">
      removed tag <a data-bind="attr: {href: '/tags/' + params.tag + '/'}, text: params.tag"></a>
      from <a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    </span>

    <span data-bind="visible: action === 'edit_title'">
      changed the title from <span data-bind="text: params.title_original"></span>
      to <a data-bind="attr: {href: nodeUrl}, text: params.title_new"></a>
    </span>

    <span data-bind="visible: action === 'project_registered'">
      registered <a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    </span>

    <span data-bind="visible: action === 'file_added'">
      added file <span data-bind="text: params.path"> to
      <a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    </span>

    <span data-bind="visible: action === 'file_removed'">
      removed file <span data-bind="text: params.path"> to
      <a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    </span>
    <span data-bind="visible: action === 'file_updated'">
      updated file <span data-bind="text: params.path"> to
      <a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    </span>

    <span data-bind="visible: action === 'node_forked'">
      created fork from <span data-bind="text: nodeCategory"></span>
      <a data-bind="attr: {href: nodeUrl}, text: nodeTitle"></a>
    </span>

  </dd>
</script>

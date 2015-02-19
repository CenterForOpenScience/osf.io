<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<div class="page-header  visible-xs">
  <h2 class="text-300">Wiki</h2>
</div>

<%def name="title()">${node['title'] | n} Wiki</%def>

<div class="row">
    <div class="col-sm-3">
        <%include file="wiki/templates/nav.mako" />
        <%include file="wiki/templates/toc.mako" />
    </div>
    <div class="col-sm-9">
        <%include file="wiki/templates/status.mako"/>
        <div id="wikiContent">
          % if not page and wiki_name != 'home':
              <p><i>This wiki page does not currently exist. Would you like to
                  <a href="edit/">create it</a>?</i></p>
          % elif not wiki_content:
              <p><em>No wiki content</em></p>
          % else:
              ${wiki_content | n}
          % endif
        </div>
    </div>
</div>

<%def name="javascript_bottom()">
<% import json %>
${parent.javascript_bottom()}
<script>
    // Update contextVars with Mako variables.
    var canEditPageName = ${json.dumps(
        all([
            'write' in user['permissions'],
            not is_edit,
            wiki_id,
            wiki_name != 'home',
            not node['is_registration']
        ])
    )};
    window.contextVars = $.extend(true, {}, window.contextVars, {
        canEditPageName: canEditPageName,
        urls: {
            wikiRename: "${urls['api']['rename']}",
            wikiBase: "${urls['web']['base']}"
        }
    })
</script>

<script src="${'/static/public/js/wiki-view-page.js' | webpack_asset}"></script>
</%def>

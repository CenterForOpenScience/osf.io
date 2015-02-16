<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<div class="page-header  visible-xs">
  <h2 class="text-300">Wiki</h2>
</div>

<%def name="title()">${node['title'] | n} Wiki</%def>

<div>
    <%include file="wiki/templates/status.mako"/>
</div>
<div class="row">
    <div class="col-sm-3 col-md-4">
        <div class="wiki-panel"> 
            <div class="wiki-panel-body"> 

                <%include file="wiki/templates/nav.mako" />
                <%include file="wiki/templates/toc.mako" />
            </div>

        </div>
    </div>
    <div class="col-sm-9 col-md-8">
        % if not page and wiki_name != 'home':
            <p><i>This wiki page does not currently exist. Would you like to
                <a href="edit/">create it</a>?</i></p>
        % else:
            <div id="markdown-it-render">${wiki_content | n}</div>
        % endif
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
        usePythonRender: ${json.dumps(use_python_render)},
        urls: {
            wikiContent: "${urls['api']['content']}",
            wikiRename: "${urls['api']['rename']}",
            wikiBase: "${urls['web']['base']}"
        }
    })
</script>

<script src="${'/static/public/js/wiki-view-page.js' | webpack_asset}"></script>
</%def>

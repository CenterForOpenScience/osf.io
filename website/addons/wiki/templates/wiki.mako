<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title'] | n} Wiki</%def>

% if user['can_comment'] or node['has_comments']:
    % if page:
        <%include file="include/comment_pane_template.mako"/>
        <%include file="include/comment_template.mako"/>
    %endif
% endif

<div class="row">
    <div class="col-sm-3">
        <%include file="wiki/templates/nav.mako" />
        <%include file="wiki/templates/toc.mako" />
    </div>
    <div class="col-sm-9">
        <%include file="wiki/templates/status.mako"/>
        % if not page and wiki_name != 'home':
            <p><i>This wiki page does not currently exist. Would you like to
                <a href="edit/">create it</a>?</i></p>
        % elif not wiki_content:
            <p><em>No wiki content</em></p>
        % else:
            <div>${wiki_content | n}</div>
        % endif
    </div>
</div>
<%def name="javascript_bottom()">
<% import json %>
${parent.javascript_bottom()}
<script>
    window.contextVars = window.contextVars || {};
    window.contextVars.wikiName = "${wiki_name}";
</script>
<script src=${"/static/public/js/wiki-page.js" | webpack_asset}></script>
</%def>
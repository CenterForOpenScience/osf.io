<%inherit file="project/addon/widget.mako"/>
<%page expression_filter="h"/>

% if wiki_raw:
    <div id="markdown-it-render" style="display: none">${wiki_raw | n}</div>
% else:
    <p><em>No wiki content</em></p>
% endif

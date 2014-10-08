<%inherit file="project/addon/widget.mako"/>
<%page expression_filter="h"/>

% if content:
    <div>${content | n}</div>
% else:
    <p><em>No wiki content</em></p>
% endif

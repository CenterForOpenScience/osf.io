<%inherit file="project/addon/widget.mako"/>

% if content:
    <div>${content}</div>
% else:
    <p><em>No wiki content</em></p>
% endif

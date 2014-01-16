<%inherit file="project/addon/widget.mako"/>

% if content:

    <div>${content}</div>
    <p><a href="${node['url']}">Read more</a></p>

% else:

    <p><em>No wiki content</em></p>

% endif

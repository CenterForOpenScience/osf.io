<%page expression_filter="h"/>

% if user['can_edit']:
<nav class="navbar navbar-default wiki-status-sm wiki-status-lg">
    <div class="navbar-collapse">
        <ul class="superlist nav navbar-nav">
            <li><a href="#" data-toggle="modal" data-target="#newWiki">New</a></li>
                <%include file="add_wiki_page.mako"/>
            <li><a href="${urls['web']['edit']}">Edit</a></li>
            % if wiki_id and wiki_name != 'home':
            <li><a href="#" data-toggle="modal" data-target="#deleteWiki">Delete</a></li>
                <%include file="delete_wiki_page.mako"/>
            % endif
        </ul>
    </div>
</nav>
% endif

<h3 class="wiki-title wiki-title-xs" id="wikiName">
    % if wiki_name == 'home':
        <i class="icon-home"></i>
    % endif
    <span id="pageName"
        % if wiki_name == 'home' and not node['is_registration']:
            data-bind="tooltip: {title: 'Note: Home page cannot be renamed.'}"
        % endif
    >${wiki_name if wiki_name != 'home' else 'Home'}</span>
    % if is_edit:
        (Draft)
    % endif
</h3>

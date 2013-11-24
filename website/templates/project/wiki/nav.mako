<nav class="subnav navbar navbar-default">
    <ul class="nav navbar-nav">

        % if is_edit:
            <li><a href="${node['url']}wiki/${pageName}">View</a></li>
        % else:
            % if user['can_edit']:
                <li><a href="${node['url']}wiki/${pageName}/edit">Edit</a></li>
            % else:
                <li><a class="disabled">Edit</a></li>
            % endif
        %endif
        % if version == 'NA':
            <li><a class="disabled">History</a></li>
        % else:
            <li><a href="${node['url']}wiki/${pageName}/compare/1">History</a> </li>
        % endif
    </ul>
</nav>

<div class="subnav">
    <ul class="nav nav-pills">
        % if is_edit:
            <li><a href="${node_url}wiki/${pageName}">View</a></li>
        % else:
            % if user_can_edit:
                <li><a href="${node_url}wiki/${pageName}/edit">Edit</a></li>
            % else:
                <li><a class="disabled">Edit</a></li>
            % endif
        %endif
        <li><a href="${node_url}wiki/${pageName}/compare/1">History</a></li>
    </ul>
</div>

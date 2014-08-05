<div class="navbar-outer" style="text-align: center;">
    <nav class="navbar navbar-default" style="display: inline-block;">
        <div class="container-fluid">
            <ul class="nav navbar-nav">
                <li><a href="${node['url']}wiki/${pageName}">View</a></li>
                % if user['can_edit']:
                    <li><a href="${node['url']}wiki/${pageName}/edit">Edit</a></li>
                % else:
                    <li><a class="disabled">Edit</a></li>
                % endif
                % if version == 'NA':
                    <li><a class="disabled">History</a></li>
                % else:
                    <li><a href="${node['url']}wiki/${pageName}/compare/1">History</a> </li>
                % endif
            </ul>
        </div>
    </nav>
</div>

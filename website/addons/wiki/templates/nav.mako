<nav class="navbar navbar-default">
    <div class="container-fluid">
        <ul class="nav navbar-nav">

            % if is_edit:
                <li><a href="${node['url']}wiki/${pageName}">View</a></li>
                <li><a href="#" data-toggle="modal" data-target="#deleteWiki">Delete</a></li>
                <%include file="delete_wiki_page.mako"/>
            % else:
                % if user['can_edit']:
                    <li><a href="${node['url']}wiki/${pageName}/edit">Edit</a></li>
                    <li><a href="#" data-toggle="modal" data-target="#newWiki">New Page</a></li>
                    <%include file="add_wiki_page.mako"/>
                % else:
                    <li><a class="disabled">Edit</a></li>
                    <li><a class="disabled">New Page</a></li>
                % endif
            %endif
            % if version == 'NA':
                <li><a class="disabled">History</a></li>
            % else:
                <li><a href="${node['url']}wiki/${pageName}/compare/1">History</a> </li>
            % endif

        </ul>
    </div><!-- end container-fluid -->
</nav>

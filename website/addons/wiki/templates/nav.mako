<%page expression_filter="h"/>

<nav class="wiki-nav">
    <div class="navbar-collapse text-center">
        <ul class="superlist nav navbar-nav" style="float: none">
            % if user['can_edit']:
            <li data-toggle="tooltip" title="New" data-placement="right" data-container="body">
                <a id="openNewWiki" href="#" data-toggle="modal" data-target="#newWiki">
                    <span class="wiki-nav-closed">
                        <i class="icon-plus-sign"></i>
                    </span> 
                </a>
            </li>
                % if wiki_id and wiki_name != 'home':
                <li data-toggle="tooltip" title="Delete" data-placement="right" data-container="body">
                    <a href="#" data-toggle="modal" data-target="#deleteWiki">
                    <span class="wiki-nav-closed"><i class="icon icon-trash text-danger"> </i></span>
                    </a>
                </li>
                % endif
            % endif
        </ul>
    </div>
</nav>

<%page expression_filter="h"/>

<nav class="wiki-nav">
    <div class="navbar-collapse text-center">
        <ul class="superlist nav navbar-nav" style="float: none">
            % if user['can_edit']:
            <li><a id="openNewWiki" href="#" data-toggle="modal" data-target="#newWiki"> 
                    <span class="wiki-nav-closed">
                        <span class="icon-stack">
                          <i class="icon-file icon-stack-base"></i>
                          <i class="icon-plus"></i>
                        </span>
                    </span> 
                </a></li>
                <%include file="add_wiki_page.mako"/>
                % if wiki_id and wiki_name != 'home':
                <li><a href="#" data-toggle="modal" data-target="#deleteWiki"> 
                    <span class="wiki-nav-closed"><i class="icon icon-trash" > </i></span> 

                    </a></li>
                    <%include file="delete_wiki_page.mako"/>
                % endif
            % endif
        </ul>
    </div>
</nav>

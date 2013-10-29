<div class="navbar navbar-fixed-top">
    <div class="navbar-inner">
        <div class="container">
            <a class="brand" style="padding-left: 10px; padding-right: 10px;" href="/">Open Science Framework<span style="font-size: 8px;"> BETA</span></a>
            <ul class="nav">
                %if user_name:
                <li><a rel="tooltip" title="My Dashboard" href="/dashboard/">Dashboard</a></li>
                %endif
                <li class='dropdown'>
                    <a href="#" class='dropdown-toggle' data-toggle='dropdown'>
                        Explore
                        <b class='caret'></b>
                    </a>
                    <ul class="dropdown-menu">
                        <li><a href="/explore">Collaborator Network</a></li>
                        <li><a href="/explore/activity">Public Activity</a></li>
                    </ul>
                </li>
                <li class='dropdown'>
                    <a href="#" class='dropdown-toggle' data-toggle='dropdown'>
                        Help<b class='caret'></b>
                    </a>
                    <ul class='dropdown-menu'>
                        <li><a href="/project/4znZP/wiki/home">About</a></li>
                        <li><a href="/faq">FAQ</a></li>
                        <li><a href="/getting-started">Getting Started</a></li>
                    </ul>
                </li>


            </ul>
            <form class="navbar-search pull-left" action="/search/" method="get">
                <input type="text" class="search-query" placeholder="Search" name="q">
            </form>
            <ul class="nav pull-right" id='navbar-icons'>
                %if user_name and display_name:
                <li><a href="/profile">${display_name}</a></li>
                ## Hide Settings button until functionality is implemented
                ##<li><a rel="tooltip" title="Settings" href="/settings"><span class='icon-white icon-cog'>&nbsp;</span></a></li>
                <li><a rel='tooltip' title='Log out' href='/logout'><span class="icon-white icon-off">&nbsp;</span></a></li>
                %else:
                    %if allow_login:
                    <li><a class="btn btn-primary" href="/account" style="background-color:rgb(0, 85, 204);;color:white;padding:5px 9px;font-size: 11px; line-height: 16px;">Create an Account or Sign-In</a></li>
                    %else:
                    %endif
                %endif
            </ul>
        </div>
    </div>
</div>

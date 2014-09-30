<div class="nav" style="display: block">

    <nav class="navbar navbar-default">

        <ul class="superlist nav navbar-nav" style="text-align: center; float: none">

        <li><a href="${node['url']}wiki/${pageName}">View</a></li>
            % if user['can_edit']:
                <li><a href="${node['url']}wiki/${pageName}/edit">Edit</a></li>
            % endif
            % if not versions:
                <li><a class="disabled">History</a></li>
            % else:
                <li><a href="${node['url']}wiki/${pageName}/compare/1">History</a> </li>
            % endif
        </ul>
    </nav>
</div>

<script type="text/javascript">
    $(document).ready(function(){
        $(".navbar-nav li").each(function(){
            var href = $(this).find('a').attr('href');
            if (href === window.location.pathname.replace(/%20/g, ' ')) {
                $(this).addClass('active');
            }
        });
    });
</script>

<%page expression_filter="h"/>

<nav class="">
    <div class="navbar-collapse text-center">
        <ul class="superlist nav navbar-nav" style="float: none">
            % if user['can_edit']:
            <li><a href="#" data-toggle="modal" data-target="#newWiki"> <i class="icon icon-file"> </i>  New Page </a></li>
                <%include file="add_wiki_page.mako"/>
                % if wiki_id and wiki_name != 'home':
                <li><a href="#" data-toggle="modal" data-target="#deleteWiki"><i class="icon icon-trash"> </i> Delete</a></li>
                    <%include file="delete_wiki_page.mako"/>
                % endif
            % endif
        </ul>
    </div>
</nav>

<script type="text/javascript">
    $(document).ready(function () {
        // special characters can be encoded differently between server/client.
        var pathname = decodeURIComponent(window.location.pathname);

        $(".navbar-nav li").each(function () {
            var $this = $(this);
            var href = decodeURIComponent($this.find('a').attr('href'));

            if (href === pathname) {
                $this.addClass('active');
            }
        });
    });
</script>

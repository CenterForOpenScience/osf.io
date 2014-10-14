<%page expression_filter="h"/>

<nav class="navbar navbar-default">
    <div class="navbar-collapse">
        <ul class="superlist nav navbar-nav" style="text-align: center; float: none">
            <li><a href="${urls['web']['page']}">View</a></li>
            % if not versions or version == 'NA':
                <li class="disabled"><a>History</a></li>
            % else:
                <li><a href="${urls['web']['compare']}">History</a></li>
            % endif
        </ul>
    </div>
</nav>

<script type="text/javascript">
    $(document).ready(function () {
        $(".navbar-nav li").each(function () {
            var $this = $(this);
            var href = $this.find('a').attr('href');
            // tilde special characters are always encoded from the server,
            // some browsers (chrome) decode them client side.
            var pathname = window.location.pathname.replace('~', '%7E');

            if (href === pathname) {
                $this.addClass('active');
            }
        });
    });
</script>

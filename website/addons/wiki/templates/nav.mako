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

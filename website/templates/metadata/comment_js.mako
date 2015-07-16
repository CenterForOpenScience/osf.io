## TODO: Is this file used anywhere?
<script type="text/javascript">

    // Asynchronous comment submission
    $('.comment-form').on('submit', function() {
        var $this = $(this);
        $.post(
            $this.attr('action'),
            $this.serialize(),
            function(response) {
                window.location.reload();
            }
        );
        return false;
    });

    $('.comment-reply').on('click', function() {
        var $this = $(this);
        $this.toggle();
        $(this).closest('.comment-container').find('form').toggle();
    });

    $('.comment-cancel').on('click', function() {
        var $this = $(this);
        $this.closest('form').toggle();
        $(this).closest('.comment-container').find('.comment-reply').toggle();
    });

</script>

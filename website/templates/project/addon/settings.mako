<div>

    <form id = "${addon_short_name}" role="form" class="addon-settings" method="POST" data-addon="${addon_short_name}">

        <!-- Title -->
        <h4>${addon_full_name}</h4>

        ${next.body()}
        
        <!-- Form feedback -->
        <div class="addon-settings-message" style="display: none; padding-top: 10px;"></div>

    </form>

</div>

${next.on_submit()}


<%def name="on_submit()">
    <script type="text/javascript">

        $(document).ready(function() {
            // Set up submission on addon settings forms
            $('#${addon_short_name}').on('submit', function() {

                var $this = $(this),
                    addon = $this.attr('data-addon'),
                    msgElm = $this.find('.addon-settings-message');

                $.ajax({
                    url: nodeApiUrl + addon + '/settings/',
                    data: JSON.stringify(formToObj($this)),
                    type: 'POST',
                    contentType: 'application/json',
                    dataType: 'json'
                }).success(function() {
                    msgElm.text('Settings updated')
                        .removeClass('text-danger').addClass('text-success')
                        .fadeOut(100).fadeIn();
                }).fail(function(xhr) {
                    var message = 'Error: ';
                    var response = JSON.parse(xhr.responseText);
                    if (response && response.message) {
                        message += response.message;
                    } else {
                        message += 'Settings not updated.'
                    }
                    msgElm.text(message)
                        .removeClass('text-success').addClass('text-danger')
                        .fadeOut(100).fadeIn();
                });

                return false;

            });
        });
    </script>
</%def>
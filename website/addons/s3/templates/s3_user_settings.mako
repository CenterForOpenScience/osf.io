<%inherit file="project/addon/settings.mako" />

<div class="form-group">
    <label for="githubRepo">Access Key</label>
    <input class="form-control" id="access_key" name="access_key" value="${access_key}" ${'disabled' if disabled else ''} />
</div>
<div class="form-group">
    <label for="githubRepo">Secret Key</label>
    <input class="form-control" id="secret_key" name="secret_key" value="${secret_key}" ${'disabled' if disabled else ''} />
</div>

<script type="text/javascript">

    function formToObj(form) {
        var rv = {};
        $.each($(form).serializeArray(), function(_, value) {
            rv[value.name] = value.value;
        });
        return rv;
    }

        // Set up submission on addon settings forms
        $('form.addon-settings').on('submit', function() {

            var $this = $(this),
                addon = $this.attr('data-addon'),
                msgElm = $this.find('.addon-settings-message');

            $.ajax({
                url: '/user/' + addon + '/settings/',
                data: JSON.stringify(formToObj($this)),
                type: 'POST',
                contentType: 'application/json',
                dataType: 'json'
            }).success(function() {
                msgElm.text('Settings updated')
                    .removeClass('text-danger').addClass('text-success')
                    .fadeOut(100).fadeIn();
            }).fail(function() {
                msgElm.text('Error: Settings not updated')
                    .removeClass('text-success').addClass('text-danger')
                    .fadeOut(100).fadeIn();
            });

            return false;

        });
</script>
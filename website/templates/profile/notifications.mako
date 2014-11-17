<%inherit file="base.mako"/>
<%def name="title()">Notifications</%def>
<%def name="content()">
<h2 class="page-header">Notifications</h2>

<div class="row">

    <div class="col-md-3">
        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                <li><a href="${ web_url_for('user_addons') }">Configure Add-ons</a></li>
                <li><a href="#">Notifications</a></li>
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-md-6">
        <div class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">Configure Email Preferences</h3></div>
            <div class="panel-body">
                 <h3>Emails</h3>
                    </br>
                    <form id="selectLists">
                        <div class="form-group">
                            <input type="checkbox"
                                   name="Open Science Framework General"
                                   ${'checked' if (mailing_lists['Open Science Framework General']) else ''}
                                    />
                            <label>Open Science Framework General</label>
                            <p class="text-muted" style="padding-left: 15px">Receive general notifications</p>
                        </div>
                        <div class="padded">
                        <button
                            type="submit"
                            id="settings-submit"
                            class="btn btn-success"
                        >Submit</button>
                        </div>
                    </form>

                    <!-- Flashed Messages -->
                    <div id="message"></div>
            </div>
            </div>
    </div>
</div>

<script>

    $('#selectLists').on('submit', function() {

        var formData = {};
        $('#selectLists').find('input').each(function (idx, elm) {
            var $elm = $(elm);
            formData[$elm.attr('name')] = $elm.is(':checked');
        });

        var submit = function () {
            var request = $.osf.postJSON('/api/v1/settings/notifications/', formData);
            request.done(function () {
                $('#message').addClass('text-success').text('Settings updated').fadeIn().fadeOut(2000);
            });
            request.fail(function () {
                var message = 'Could not update settings.';
                $('#message').addClass('text-danger').text(message).fadeIn().fadeOut(2000);

            });
        };

        submit();
        return false;
    });


</script>

</%def>

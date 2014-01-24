<%inherit file="project/addon/user_settings.mako" />

% if authorized:

    ## You are authorized

    <a id="dataverseDelKey" class="btn btn-danger">Unlink Dataverse Account</a>
    <div style="padding-top: 10px;">
        Authorized by Dataverse user ${authorized_dataverse_user}
    </div>

% else:

    ## Show auth fields
    <div class="form-group">
        <label for="dataverseUsername">Dataverse Username</label>
        <input class="form-control" id="dataverseUsername" name="dataverse_username" />
    </div>
    <div class="form-group">
        <label for="dataversePassword">Dataverse Password</label>
        <input class="form-control" id="dataversePassword" type="password" name="dataverse_password" />
    </div>
    <a id="dataverseLinkAccount" class="btn btn-success">Link to Dataverse</a>

% endif

<script type="text/javascript">

    $(document).ready(function() {

        $('#dataverseDelKey').on('click', function() {
             bootbox.confirm(
                'Are you sure you want to unlink your Dataverse Account? This will ' +
                    'revoke access to Dataverse for all projects you have authorized. ' +
                    'Your OSF collaborators will not be able to access any of the ' +
                    'Dataverse studies that you have authorized.',
                function(result) {
                    if (result) {
                        $.ajax({
                            url: '/api/v1/settings/dataverse/delete/',
                            type: 'POST',
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                window.location.reload();
                            }
                        });
                    }
                }
            )
        });

        $('#dataverseLinkAccount').on('click', function() {
            var msgElm = $('#addonSettingsDataverse .addon-settings-message');
            $.ajax({
                url: '/api/v1/settings/dataverse/',
                data: JSON.stringify(AddonHelper.formToObj($('#addonSettingsDataverse'))),
                type: 'POST',
                contentType: 'application/json',
                dataType: 'json',
            }).success(function() {
                window.location.reload();
            }).fail(function() {
                var message = 'Error: Login was unsuccessful';
                msgElm.text(message)
                    .removeClass('text-success').addClass('text-danger')
                    .fadeOut(100).fadeIn();
            });
        });

    });

</script>

<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>
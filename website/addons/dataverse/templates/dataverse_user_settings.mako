<%inherit file="project/addon/settings.mako" />

% if authorized:

    ## You are authorized
    ## Todo: Show delete acct form
    <a id="dataverseDelKey" class="btn btn-danger">Delete User Validation</a>

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
    <a id="dataverseAuthenticate" class="btn btn-primary">
        Authenticate
    </a>

% endif

<script type="text/javascript">

    $(document).ready(function() {

        $('#dataverseAuthenticate').on('click', function() {
            % if authorized_dataverse_user:
                $.ajax({
                    type: 'POST',
                    url: '/settings/dataverse/',
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        window.location.reload();
                    }
                });
            % else:
                $.ajax({
                    type: 'POST',
                    url: '/settings/dataverse/',
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        window.location.reload();
                    }
                });
            % endif
        });

    });

</script>

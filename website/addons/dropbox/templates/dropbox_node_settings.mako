<h4>
    ${addon_full_name}
</h4>

<div class="well well-sm">
    Authorized by ${owner_info.get('display_name', 'Dropbox user')}</a>
    % if user_has_auth:
        <a id="dropboxRemoveToken" class="text-danger pull-right" style="cursor: pointer">Deauthorize</a>
    % endif
</div>

<div id="dropboxScope">
    <div class="row">
        <div class="col-md-12">
            <form class="form" data-bind="submit: submitSettings">
                <div class="form-group">
                    <select class="form-control" data-bind="options: folders, value: selected"></select>
                </div>
                <input type='submit' value="Submit" class="btn btn-success" />
            </form>
        </div>
    </div>
</div><!-- end #dropboxScope -->

<!-- <script src="/addons/static/dropbox/dropboxConfigHelper.js"></script> -->

<script>
    $script(['/addons/static/dropbox/dropbox.min.js', '/addons/static/dropbox/dropboxConfigHelper.js'], 'dropbox');

    $script.ready('dropbox', function() {
        var client = new Dropbox.Client({
            key: 'ssiprvsldytku7f'
        });
        client.authDriver(new Dropbox.AuthDriver.Redirect());
        client.authenticate(function(error, client) {
            if (error) {
                console.log('Could not authenticate with Dropbox');
            }
        });
    });
</script>

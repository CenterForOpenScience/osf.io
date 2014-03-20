<h4>
    ${addon_full_name}
    % if node_has_auth:
    <small> Authorized by ${owner_info.get('display_name', 'Dropbox user')}</small>
        %if user_has_auth:
            <small  class="pull-right" >
                <a id="dropboxDelKey" class="text-danger" style="cursor: pointer">Deauthorize</a>
            </small>
        %endif
    %endif
</h4>

<div id="dropboxScope">
    <div class="row">
        <div class="col-md-12">
            <form class="form" data-bind="submit: submitSettings">
                <div class="form-group">
                    <label>Folder</label>
                    <select class="form-control" data-bind="options: folders, value: selected"></select>
                </div>
                <input type='submit' value="Choose" class="btn btn-primary" />
            </form>
        </div>
    </div>
</div><!-- end #dropboxScope -->

<script src="/addons/static/dropbox/nodeSettings.js"></script>

<script>
    $(function() {
        var dropbox = new DropboxConfigHelper('#dropboxScope', ['foo', 'bar', 'baz']);
    });
</script>

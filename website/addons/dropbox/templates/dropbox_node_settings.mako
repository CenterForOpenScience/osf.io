<h4>
    ${addon_full_name}
</h4>


<div id="dropboxScope">
    <pre data-bind="text: ko.toJSON($data, null, 2)"></pre>
    <div class="well well-sm">
        Authorized by {{ ownerName }}</a>
        % if user_has_auth:
            <a id="dropboxRemoveToken" class="text-danger pull-right" style="cursor: pointer">Deauthorize</a>
        % endif
    </div>
    <div class="row">
        <div class="col-md-12">
            <form class="form" data-bind="submit: submitSettings">
                <div class="form-group">
                    <select class="form-control" data-bind="options: folders, value: selected"></select>
                </div>
                <input type='submit' value="Submit" class="btn btn-success" />

                <p data-bind="attr: {class: messageClass}">
                    {{message}}
                </p>
            </form>
        </div>
    </div>
</div><!-- end #dropboxScope -->

<script src="/addons/static/dropbox/dropboxConfigHelper.js"></script>

<script>
    $(function() {
        var url = '${node["api_url"] + "dropbox/config/"}';
        var dropbox = new DropboxConfigManager('#dropboxScope', url);
    });
</script>

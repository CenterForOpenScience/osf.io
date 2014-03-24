<h4>
    ${addon_full_name}
</h4>


<div id="dropboxScope">
    <div data-bind='if: nodeHasAuth'>
        <div class="well well-sm">
            Authorized by {{ ownerName }}</a>
            <span data-bind="visible: userHasAuth">
                <a data-bind="click: deauthorize"
                    class="text-danger pull-right">Deauthorize</a>
            </span>
        </div><!-- end well -->
        <div class="row">
            <div class="col-md-12">
                <form class="form" data-bind="submit: submitSettings">
                    <div class="form-group">
                        <select class="form-control" data-bind="options: folders, value: selected"></select>
                    </div>
                    <input type='submit' value="Choose folder" class="btn btn-success" />
                    <p data-bind="text: message, attr: {class: messageClass}"></p>
                </form>
            </div><!-- end col -->
        </div><!-- end row -->
    </div>

    <div data-bind="if: userHasAuth && !nodeHasAuth">
        <a data-bind="click: importAuth" href="#" class="btn btn-primary">
            Authorize: Import Access Token from Profile
        </a>
    </div>

    <div data-bind="if: !userHasAuth && !nodeHasAuth">
        <a data-bind="attr: {href: urls.auth}" class="btn btn-primary">
            Authorize: Create Access Token
        </a>
    </div>
</div><!-- end #dropboxScope -->

<script src="/addons/static/dropbox/dropboxConfigHelper.js"></script>

<script>
    $(function() {
        var url = '${node["api_url"] + "dropbox/config/"}';
        var dropbox = new DropboxConfigManager('#dropboxScope', url);
    });
</script>

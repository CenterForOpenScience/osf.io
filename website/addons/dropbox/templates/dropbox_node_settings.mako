<h4>
    ${addon_full_name}
</h4>


<div id="dropboxScope" class="scripted">
    <!-- <pre data-bind="text: ko.toJSON($data, null, 2)"></pre> -->
    <div data-bind='if: showSettings'>
        <div class="well well-sm">
            Authorized by <span data-bind="text: ownerName"></span></a>
            <span data-bind="visible: userHasAuth">
                <a data-bind="click: deauthorize"
                    class="text-danger pull-right">Deauthorize</a>
            </span>
        </div><!-- end well -->
        <div class="row">
            <div class="col-md-12">
                <p><strong>Shared Folder:
                    </strong><pre data-bind="text: selected"></pre>
                </p>
                <button data-bind="click: togglePicker, css: {active: showPicker}" class="btn btn-default">Select Folder</button>

                <div data-bind="if: showPicker">
                    <p class="help-block">Click the
                        <button class="btn btn-success btn-mini" disabled><i class="icon-share"></i></button> icon next to a folder to link it with this project.</p>
                    <div id="myGrid" class="filebrowser hgrid"></div>
                </div>

            </div><!-- end col -->
        </div><!-- end row -->
    </div>

    <div data-bind="if: showImport">
        <a data-bind="click: importAuth" href="#" class="btn btn-primary">
            Authorize: Import Access Token from Profile
        </a>
    </div>

    <div data-bind="if: showTokenCreateButton">
        <a data-bind="attr: {href: urls.auth}" class="btn btn-primary">
            Authorize: Create Access Token
        </a>
    </div>

    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
</div><!-- end #dropboxScope -->


<script>
    $script(['/addons/static/dropbox/dropboxConfigHelper.js']);
    $script.ready('dropboxConfigManager', function() {
        var url = '${node["api_url"] + "dropbox/config/"}';
        window.dropbox = new DropboxConfigManager('#dropboxScope', url);
    });
</script>

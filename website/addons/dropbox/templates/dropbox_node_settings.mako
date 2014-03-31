<link rel="stylesheet" href="/static/addons/dropbox/dropbox.css">

<h4 class="addon-title">
    Dropbox
</h4>

<div id="dropboxScope" class="scripted">
    <pre data-bind="text: ko.toJSON($data, null, 2)"></pre>

    <!-- Settings Pane -->
    <div class="dropbox-settings" data-bind='if: showSettings'>
        <div class="well well-sm">
            <span class="authorized-by">
                Authorized by <a data-bind="attr.href: urls().owner">
                    {{ownerName}}
                </a>
            </span>
            <span data-bind="visible: userHasAuth">
                <a data-bind="click: deauthorize"
                    class="text-danger pull-right">Deauthorize</a>
            </span>
        </div><!-- end well -->
        <div class="row">
            <div class="col-md-12">
                <p><strong>Current Folder:</strong></p>

                <!-- The linked folder -->
                <h4 class="selected-folder">
                    <i class="icon-folder-close-alt"></i>
                    <a data-bind="attr.href: urls().files"class='selected-folder-name'>
                        {{folderName}}
                    </a>
                </h4>

                <!-- Folder buttons -->
                <button data-bind="click: togglePicker,
                                    css: {active: currentDisplay() === PICKER}"
                        class="btn btn-sm btn-default">Change</button>

                <button data-bind="visible: urls().share, click: toggleShare,
                                    css: {active: currentDisplay() === SHARE}"
                    class="btn btn-sm btn-default">Share on Dropbox</button>

                <!-- Folder picker -->
                <img class="scripted" id='dropboxProgBar' src="/static/addons/dropbox/loading-bars.svg" alt="Loading folders..."/>
                <div data-bind="if: currentDisplay() === PICKER">
                    <div id="myGrid"
                         class="filebrowser hgrid dropbox-folder-picker"></div>
                </div>

                <!-- Share -->
                <div data-bind="if: currentDisplay() === SHARE">
                    <ul data-bind="foreach: {data: emails, as: 'email'}">
                        <li>{{email}}</li>
                    </ul>
                    <a data-bind="attr.href: urls().share" class="btn btn-default">Continue to Dropbox</a>
                </div>

                <!-- Queued selection -->
                <div class="dropbox-confirm-selection"
                    data-bind="if: selected">
                    <form data-bind="submit: submitSettings">

                        <h4 class="dropbox-confirm-dlg">
                            Connect &ldquo;{{ selectedFolderName }}&rdquo;?
                        </h4>
                        <div class="pull-right">
                            <button class="btn btn-default"
                                    data-bind="click: cancelSelection">Cancel</button>
                            <input type="submit"
                                    class="btn btn-primary"
                                    value="Submit">
                        </div>
                    </form>
                </div>

            </div><!-- end col -->
        </div><!-- end row -->
    </div><!-- end .dropbox-settings -->

     <!-- Import Access Token Button -->
    <div data-bind="if: showImport">
        <a data-bind="click: importAuth" href="#" class="btn btn-primary">
            Authorize: Import Access Token from Profile
        </a>
    </div>

    <!-- Oauth Start Button -->
    <div data-bind="if: showTokenCreateButton">
        <a data-bind="attr.href: urls().auth" class="btn btn-primary">
            Authorize: Create Access Token
        </a>
    </div>

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr.class: messageClass"></p>
    </div>
</div><!-- end #dropboxScope -->


<script>
    $script(['/static/addons/dropbox/dropboxNodeConfig.js']);
    $script.ready('dropboxNodeConfig', function() {
        // TODO(sloria): Remove this dependency on mako variable
        var url = '${node["api_url"] + "dropbox/config/"}';
        var dropbox = new DropboxNodeConfig('#dropboxScope', url, '#myGrid');
    });
</script>

<div id="figshareScope" class="scripted">
    <!-- <pre data-bind="text: ko.toJSON($data, null, 2)"></pre> -->
    <h4 class="addon-title">
    	FigShare
        <span data-bind="if: nodeHasAuth">
            <small class="authorized-by">
                authorized by <a data-bind="attr.href: urls().owner">
                    {{ownerName}}
                </a>
            </small>
            <small data-bind="visible: userHasAuth">
                <a data-bind="click: deauthorize"
                    class="text-danger pull-right">Deauthorize</a>
            </small>
        </span>
    </h4>


    <!-- Settings Pane -->
    <div class="figshare-settings" data-bind='if: showSettings'>
        <div class="row">
            <div class="col-md-12">
                <p><strong>Current Folder:</strong></p>

                <!-- The linked folder -->
                <div class="selected-folder">
                    <i data-bind="visible: folder().name" class="icon-folder-close-alt"></i>
                    <a data-bind="attr.href: urls().files"class='selected-folder-name'>
                        {{folderName}}
                    </a>

                    <p data-bind="if: folder().path === null" class="text-muted">No folder selected</p>
                </div>

                <!-- Folder buttons -->
                <div class="btn-group">
                    <button data-bind="click: togglePicker,
                                        css: {active: currentDisplay() === PICKER}"
                            class="btn btn-sm btn-figshare"><i class="icon-edit"></i> Change</button>
                    <button data-bind="attr.disabled: disableShare,
                                        click: toggleShare,
                                        css: {active: currentDisplay() === SHARE}"
                        class="btn btn-sm btn-figshare"><i class="icon-share-alt"></i> Share on Figshare
                            <span data-bind="visible: folder().path === '/'">(Cannot share root folder)</span>
                        </button>
                </div>


                <!-- Folder picker -->
                <div class="figshare-widget">
                    <p class="text-muted text-center figshare-loading-text" data-bind="visible: loading">
                    Loading folders...</p>

                    <div data-bind="if: currentDisplay() === PICKER">
                        <div id="myGrid"
                             class="filebrowser hgrid figshare-folder-picker"></div>
                    </div>

                    <!-- Share -->
                    <div data-bind="if: currentDisplay() === SHARE && emails().length === 0"
                        class="help-block">
                        <p>No contributors to share with.</p>
                    </div>

                    <div data-bind="if: currentDisplay() === SHARE && emails().length">
                        <div class="help-block">
                            <p>To share this folder with other Figshare users on this project, copy
                            the email addresses of the contributors (listed below) into the
                            "Share Folder" dialog on Figshare.</p>
                        </div>

                        <label for="contrib-emails">Copy these:</label>
                        <div class="input-group">
                            <textarea name="contrib-emails"
                                    class="form-control" rows="3" id="contribEmails"
                             data-bind="value: emailList,
                                        attr.autofocus: currentDisplay() === SHARE">
                            </textarea>
                            <span data-clipboard-target="contribEmails"
                                class="input-group-addon pointer"
                                id="copyBtn">
                                <i class="icon-paste"></i>
                            </span>
                        </div>

                        <div class="input-group pull-right">
                            <a target="_blank" data-bind="attr.href: urls().share"
                                class="btn btn-link"><i class="icon-share-alt"></i> Continue to Figshare...</a>
                        </div>
                    </div>

                    <!-- Queued selection -->
                    <div class="figshare-confirm-selection"
                        data-bind="visible: currentDisplay() == PICKER">
                        <form data-bind="submit: submitSettings">

                            <h4 data-bind="if: selected" class="figshare-confirm-dlg">
                                Connect &ldquo;{{ selectedFolderName }}&rdquo;?
                            </h4>
                            <div class="pull-right">
                                <button class="btn btn-default"
                                        data-bind="click: cancelSelection,
                                                    visible: selected()">Cancel</button>
                                <input data-bind="attr.disabled: !selected()"
                                        type="submit"
                                        class="btn btn-primary"
                                        value="Submit">
                            </div>
                        </form>
                    </div><!-- end .figshare-confirm-selection -->

                </div>
            </div><!-- end col -->
        </div><!-- end row -->
    </div><!-- end .figshare-settings -->

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
</div><!-- end #figshareScope -->


<script>
    $script(['/static/vendor/bower_components/zeroclipboard/ZeroClipboard.js'],
            'zeroclipboard');

    $script.ready('zeroclipboard', function() {
        ZeroClipboard.config({moviePath: '/static/vendor/bower_components/zeroclipboard/ZeroClipboard.swf'})
    })
    $script(['/static/addons/figshare/figshareNodeConfig.js']);
    $script.ready('figshareNodeConfig', function() {
        // TODO(sloria): Remove this dependency on mako variable
        var url = '${node["api_url"] + "figshare/config/"}';
        var figshare = new FigshareNodeConfig('#figshareScope', url, '#myGrid');
    });
</script>

<div id="${addon_short_name}Scope" class="scripted">
    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}></img>
        ${addon_full_name}
        <small class="authorized-by">
            <span data-bind="if: nodeHasAuth">
                authorized by <a data-bind="attr.href: urls().owner">
                    {{ownerName}}
                </a>
                % if not is_registration:
                    <a data-bind="click: deauthorize"
                        class="text-danger pull-right addon-auth">Disconnect Account</a>
                % endif
            </span>

             <!-- Import Access Token Button -->
            <span data-bind="if: showImport">
                <a data-bind="click: importAuth" href="#" class="text-primary pull-right addon-auth">
                    Import Account From Profile
                </a>
            </span>

            <!-- Loading Import Text -->
            <span data-bind="if: showLoading">
                <p class="text-muted pull-right addon-auth">
                    Loading ...
                </p>
            </span>

            <!-- Oauth Start Button -->
            <span data-bind="if: showTokenCreateButton">
                <a data-bind="click: connectAccount" class="text-primary pull-right addon-auth">
                  Connect Account
                </a>
            </span>
        </small>
    </h4>
    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings" data-bind="visible: showSettings">
        <div class="row">
            <div class="col-md-12">
                <p class="break-word">
                    <strong>Current Folder:</strong>
                    <a data-bind="ifnot: folderName() === '', attr.href: urls().files">
                        {{folderName}}
                    </a>
                    <span data-bind="if: folderName() === ''" class="text-muted">
                        None
                    </span>
                </p>
                <!-- Folder buttons -->
                <div class="btn-group" data-bind="visible: userIsOwner() && validCredentials()">
                    <button data-bind="click: togglePicker,
                                       css: {active: currentDisplay() === PICKER}" class="btn btn-sm btn-addon"><i class="icon-edit"></i> Change</button>
                </div>
                <!-- Folder picker -->
                <div class="addon-folderpicker-widget ${addon_short_name}-widget">
                    <p class="text-muted text-center ${addon_short_name}-loading-text" data-bind="visible: loading">
                        Loading folders...</p>
                    <div data-bind="visible: currentDisplay() === PICKER">
                        <div id="${addon_short_name}Grid" class="filebrowser ${addon_short_name}-folder-picker"></div>
                    </div>
                    <!-- Queued selection -->
                    <div class="${addon_short_name}-confirm-selection" data-bind="visible: currentDisplay() == PICKER && selected()">
                        <form data-bind="submit: submitSettings">
                            <div class="break-word">
                                <h4 data-bind="if: selected" class="${addon_short_name}-confirm-dlg">
                                    Connect &ldquo;{{ selectedFolderName }}&rdquo;?
                                </h4>
                            </div>
                            <div class="pull-right">
                                <button class="btn btn-default" data-bind="click: cancelSelection">
                                    Cancel
                                </button>
                                <input type="submit" class="btn btn-success" value="Save" />
                            </div>
                        </form>
                    </div>         
                </div>
            </div>
            <!-- end col -->
        </div>
        <!-- end row -->
    </div>
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr.class: messageClass"></p>
    </div>
</div>

<div id="${addon_short_name}Scope" class="scripted">
    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url} aria-label="${addon_full_name} icon" alt="${addon_full_name} icon">
        ${addon_full_name}
        <small class="authorized-by">
            <span data-bind="if: nodeHasAuth">
                authorized by <a data-bind="attr: {href: urls().owner}, text: ownerName"></a>
                % if not is_registration:
                    <a data-bind="click: deauthorize, visible: validCredentials"
                        class="text-danger pull-right addon-auth">Disconnect Account</a>
                % endif
            </span>

             <!-- Import Access Token Button -->
            <span data-bind="if: showImport">
                <a data-bind="click: importAuth" href="#" class="text-primary pull-right addon-auth">
                    Import Account from Profile
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
    <!-- Library Pane -->
    <div class="library-settings" data-bind='visible: showSettings'>
        <div class="row">
            <div class="col-md-12">
                <p class="break-word">
                    <strong>Current Library:</strong>
                    <span data-bind="if: libraryName">
                        <a data-bind="attr: {href: urls().files}, text: libraryName"></a>
                    </span>
                    <span class="text-muted" data-bind="ifnot: libraryName">
                        None
                    </span>
                </p>
            </div>
        </div>
        <!-- Library buttons -->
        <div class="btn-group" data-bind="visible: userIsOwner() && validCredentials()">
            <button  data-bind="click: toggleLibraryPicker" class="btn btn-primary">
                <span data-bind="text: toggleChangeLibraryText"></span>
            </button>
        </div>
        <!-- Library picker -->
        <p class="text-muted text-center ${addon_short_name}-loading-text" data-bind="visible: libraryLoading">
            Loading libraries...
        </p>
        <div data-bind="visible: toggleChangeLibraryText() === 'Close' & !libraryLoading()">
            <form data-bind="submit: saveLibrary">
                <div class="tb-table m-v-sm" style="width:100%; overflow-y: scroll; height: 200px;" data-bind="event: { scroll: scrolled }">
                    <div class="tb-row-titles">
                        <div class="tb-th" data-tb-th-col="0" style="width: 75%">
                            Libraries
                        </div>
                        <div class="tb-th" data-tb-th-col="1" style="width: 25%, border-left: 1px solid #CCC;">
                            Select
                        </div>
                    </div>
                    <div class="tb-tbody" style="border-left: 1px solid #EEE;border-right: 1px solid #EEE;" data-bind="foreach: libraries">
                        <div class="tb-row" style="display:block; width:100%;">
                            <div class="tb-td" style="width: 75%" data-bind="text: name"></div>
                            <div style="width:10%;" class="tb-td">
                                <input data-bind="attr: {value: id + ',' + name}, checked: $root.selectedLibrary, event: { click: $root.onLibraryChange()}" name="library-group" type="radio">
                            </div>
                        </div>
                    </div>
                </div>
                <div class="pull-right" data-bind="visible: selectedLibrary() && currentLibraryDisplay()">
                   <button class="btn btn-default" data-bind="click: cancelLibrarySelection">
                       Cancel
                   </button>
                   <input type="submit" class="btn btn-success" value="Save" />
                </div>
                <div class="clearfix"></div>
            </form>
        </div>
    </div>
    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings" data-bind='visible: showSettings && libraryName'>
        <div class="row">
            <div class="col-md-12 m-t-sm">
                <p class="break-word">
                    <strong>Current Folder:</strong>
                    <span data-bind="if: folderName">
                        <a data-bind="attr: {href: urls().files}, text: folderName"></a>
                    </span>
                    <span class="text-muted" data-bind="ifnot: folderName">
                        None
                    </span>
                </p>
                <!-- Folder buttons -->
                <div class="btn-group" data-bind="visible: userIsOwner() && validCredentials()">
                    <button data-bind="click: togglePicker,
                                       css: {active: currentDisplay() === PICKER}" class="btn btn-primary">
                                       <span data-bind="text: toggleChangeText"></span></button>
                </div>
                <!-- Folder picker -->
                <div class="m-t-sm addon-folderpicker-widget ${addon_short_name}-widget">
                    <p class="text-muted text-center ${addon_short_name}-loading-text" data-bind="visible: loading">
                        Loading folders...</p>
                    <div data-bind="visible: currentDisplay() === PICKER">
                        <div id="${addon_short_name}Grid" class="filebrowser ${addon_short_name}-folder-picker"></div>
                    </div>
                    <!-- Queued selection -->
                    <div class="${addon_short_name}-confirm-selection" data-bind="visible: currentDisplay() == PICKER && selected()">
                        <form data-bind="submit: submitSettings">
                            <div class="break-word">
                                <div data-bind="if: selected" class="alert alert-info ${addon_short_name}-confirm-dlg">
                                    Connect <b>&ldquo;<span data-bind="text: selectedFolderName"></span>&rdquo;</b>?
                                </div>
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
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
</div>

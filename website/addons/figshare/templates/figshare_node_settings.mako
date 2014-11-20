<link rel="stylesheet" href="/static/addons/figshare/figshare.css">

<div id="figshareScope" class="scripted">
    <!-- <pre data-bind="text: ko.toJSON($data, null, 2)"></pre> -->
    <h4 class="addon-title">
    	Figshare
        <small class="authorized-by">
            <span data-bind="if: nodeHasAuth">
                authorized by <a data-bind="attr.href: urls().owner">
                    {{ownerName}}
                </a>
                % if not is_registration:
                    <a data-bind="click: deauthorize"
                           class="text-danger pull-right addon-auth">
                      Deauthorize
                    </a>
                %endif
            </span>

             <!-- Import Access Token Button -->
            <span data-bind="if: showImport">
                <a data-bind="click: importAuth" href="#" class="text-primary pull-right addon-auth">
                    Import Access Token
                </a>
            </span>

            <!-- Oauth Start Button -->
            <span data-bind="if: showTokenCreateButton">
                <a data-bind="attr.href: urls().auth" class="text-primary pull-right addon-auth">
                    Create Access Token
                </a>
            </span>

        </small>
    </h4>

    <!-- Settings Pane -->
    <div class="figshare-settings" data-bind='if: showSettings'>
        <div class="row">
            <div class="col-md-12">
                <p>
                    <strong>Current Linked Content:</strong>

                    <a data-bind="attr.href: urls().files">
                        {{folderName}}
                    </a>
                    <span data-bind="if: linked().id === null" class="text-muted">
                        None
                    </span>
                </p>

                <!-- Folder buttons -->
                <div class="btn-group" data-bind="visible: userIsOwner">
                    <button data-bind="click: togglePicker,
                                        css: {active: currentDisplay() === PICKER}"
                            class="btn btn-sm btn-figshare"><i class="icon-edit"></i> Change</button>
                </div>


                <!-- Folder picker -->
                <div class="figshare-widget">
                    <p class="text-muted text-center figshare-loading-text" data-bind="visible: loading">
                    Loading folders...</p>

                    <div data-bind="if: currentDisplay() === PICKER">
                        <div id="figshareGrid"
                             class="filebrowser hgrid figshare-folder-picker"></div>
                    </div>
            
                    <!-- Queued selection -->
                    <div class="figshare-confirm-selection"
                        data-bind="visible: currentDisplay() === PICKER && selected()">
                        <form data-bind="submit: submitSettings">

                            <h4 data-bind="if: selected" class="figshare-confirm-dlg">
                                Connect Figshare {{selectedFolderType}} &ldquo;{{ selectedFolderName }}&rdquo;?
                            </h4>
                            <div class="pull-right">
                                <button class="btn btn-default"
                                        data-bind="click: cancelSelection">
                                    Cancel
                                </button>
                                <input type="submit"
                                       class="btn btn-primary"
                                       value="Submit" />
                            </div>
                        </form>
                    </div><!-- end .figshare-confirm-selection -->

                </div>
            </div><!-- end col -->
        </div><!-- end row -->
    </div><!-- end .figshare-settings -->

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr.class: messageClass"></p>
    </div>
</div><!-- end #figshareScope -->


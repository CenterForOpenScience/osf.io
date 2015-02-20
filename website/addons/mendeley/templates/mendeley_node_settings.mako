<div id="mendeleyScope" class="scripted">
    <h4 class="addon-title">
        Mendeley
        <small class="authorized-by">
            <span data-bind="if: nodeHasAuth">
                authorized by <a data-bind="attr.href: urls().owner">
                    {{ownerName}}
                </a>
                % if not is_registration:
                    <a data-bind="click: deauthorize"
                        class="text-danger pull-right addon-auth">Deauthorize</a>
                % endif
            </span>

             <!-- Import Access Token Button -->
            <span data-bind="if: showImport">
                <a data-bind="click: importAuth" href="#" class="text-primary pull-right addon-auth">
                    Import Access Token
                </a>
            </span>

            <!-- Oauth Start Button -->
            <span data-bind="if: showTokenCreateButton">
            <a data-bind="click: connectAccount" class="text-primary pull-right addon-auth">Create Access Token</a>
            </span>
        </small>
    </h4>

    <!-- Settings Pane -->
    <div class="mendeley-settings" data-bind='if: showSettings'>
        <div class="row">
            <div class="col-md-12">
                <p>
                    <strong>Current Folder:</strong>
                             {{folder}}
                    <span data-bind="if: folder().path === null" class="text-muted">
                        None
                    </span>

                </p>

                <!-- Folder buttons -->
                <div class="btn-group" data-bind="visible: userIsOwner()">
                    <button data-bind="visible: validCredentials,
                                        click: togglePicker,
                                        css: {active: currentDisplay() === PICKER}"
                            class="btn btn-sm btn-addon"><i class="icon-edit"></i> Change</button>
                            <span data-bind="visible: folder().path === '/'">(Cannot share root folder)</span>
                        </button>
                </div>


                <!-- Folder picker -->
                <div class="mendeley-widget">
                    <p class="text-muted text-center mendeley-loading-text" data-bind="visible: loading">
                    Loading folders...</p>

                    <div data-bind="visible: currentDisplay() === PICKER">
                        <div id="mendeleyGrid"
                             class="filebrowser mendeley-folder-picker"></div>
                    </div>

                    <!-- Queued selection -->
                    <div class="mendeley-confirm-selection"
                        data-bind="visible: currentDisplay() == PICKER && selected()">
                        <form data-bind="submit: submitSettings">

                            <h4 data-bind="if: selected" class="mendeley-confirm-dlg">
                                Connect &ldquo;{{ selectedFolderName }}&rdquo;?
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
                    </div><!-- end .mendeley-confirm-selection -->

                </div>
            </div><!-- end col -->
        </div><!-- end row -->
    </div><!-- end .mendeley-settings -->

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr.class: messageClass"></p>
    </div>
</div><!-- end #mendeleyScope -->

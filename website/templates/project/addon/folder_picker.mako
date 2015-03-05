<div id="${addon_short_name}Scope" class="scripted">
    <h4 class="addon-title">
    ${addon_full_name}        
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
                <a data-bind="attr.href: urls().auth" class="text-primary pull-right addon-auth">
                    Create Access Token
                </a>
            </span>
        </small>
    </h4>
    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings" data-bind='if: showSettings'>
        <div class="row">
            <div class="col-md-12">
                <p>
                    <strong>Current Folder:</strong>
                    <a data-bind="attr.href: urls().files">
                        {{folderName}}
                    </a>
                    <span data-bind="if: folder().path === null" class="text-muted">
                        None
                    </span>
                </p>
                <!-- Folder buttons -->
                <div class="btn-group" data-bind="visible: userIsOwner() && validCredentials()">
                    <button data-bind="click: togglePicker,
                                       css: {active: currentDisplay() === PICKER}" class="btn btn-sm btn-addon"><i class="icon-edit"></i> Change</button>
                    <button data-bind="attr.disabled: disableShare,
                                       visible: urls().emails,
                                       click: toggleShare,
                                       css: {active: currentDisplay() === SHARE}" class="btn btn-sm btn-addon"><i class="icon-share-alt"></i> Share on ${addon_full_name}
                        <span data-bind="visible: folder().path === '/'">(Cannot share root folder)</span>
                    </button>
                </div>
                <!-- Folder picker -->
                <div class="${addon_short_name}-widget">
                    <p class="text-muted text-center ${addon_short_name}-loading-text" data-bind="visible: loading">
                        Loading folders...</p>
                    <div data-bind="visible: currentDisplay() === PICKER">
                        <div id="${addon_short_name}Grid" class="filebrowser ${addon_short_name}-folder-picker"></div>
                    </div>

                    <!-- Share -->
                    <div data-bind="visible: currentDisplay() === SHARE && emails().length === 0" class="help-block">
                        <p>No contributors to share with.</p>
                    </div>

                    <div data-bind="visible: currentDisplay() === SHARE && emails().length">
                        <div class="help-block">
                            <p>To share this folder with other ${addon_full_name} users on this project, copy the email addresses of the contributors (listed below) into the "Share Folder" dialog on ${addon_full_name}.</p>
                        </div>
                        <label for="contrib-emails">Copy these:</label>
                        <div class="input-group">
                            <textarea name="contrib-emails" class="form-control" rows="3" id="contribEmails" data-bind="value: emailList,
                                        attr.autofocus: currentDisplay() === SHARE">
                            </textarea>
                            <span data-clipboard-target="contribEmails" class="input-group-addon pointer" id="copyBtn">
                                <i class="icon-paste"></i>
                            </span>
                        </div>
                        <div class="input-group pull-right">
                            <a target="_blank" data-bind="attr.href: urls().share" class="btn btn-link"><i class="icon-share-alt"></i> Continue to ${addon_full_name}...</a>
                        </div>
                    </div>
                    <!-- Queued selection -->
                    <div class="${addon_short_name}-confirm-selection" data-bind="visible: currentDisplay() == PICKER && selected()">
                        <form data-bind="submit: submitSettings">
                            <div class="pull-right">
                                <button class="btn btn-default" data-bind="click: cancelSelection">
                                    Cancel
                                </button>
                                <input type="submit" class="btn btn-primary" value="Submit" />
                            </div>
                            <h4 data-bind="if: selected" class="${addon_short_name}-confirm-dlg">
                                Connect &ldquo;{{ selectedFolderName }}&rdquo;?
                            </h4>
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

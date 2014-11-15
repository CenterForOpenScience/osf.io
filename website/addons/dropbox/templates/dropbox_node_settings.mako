
<link rel="stylesheet" href="/static/addons/dropbox/dropbox.css">
<div id="dropboxScope" class="scripted">
    <!-- <pre data-bind="text: ko.toJSON($data, null, 2)"></pre> -->
    <h4 class="addon-title">
        Dropbox
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
    <div class="dropbox-settings" data-bind='if: showSettings'>
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
                <div class="btn-group" data-bind="visible: userIsOwner()">
                    <button data-bind="visible: validCredentials,
                                        click: togglePicker,
                                        css: {active: currentDisplay() === PICKER}"
                            class="btn btn-sm btn-dropbox"><i class="icon-edit"></i> Change</button>
                    <button data-bind="attr.disabled: disableShare,
                                        visible: validCredentials,
                                        click: toggleShare,
                                        css: {active: currentDisplay() === SHARE}"
                        class="btn btn-sm btn-dropbox"><i class="icon-share-alt"></i> Share on Dropbox
                            <span data-bind="visible: folder().path === '/'">(Cannot share root folder)</span>
                        </button>
                </div>


                <!-- Folder picker -->
                <div class="dropbox-widget">
                    <p class="text-muted text-center dropbox-loading-text" data-bind="visible: loading">
                    Loading folders...</p>

                    <div data-bind="visible: currentDisplay() === PICKER">
                        <div id="myDropboxGrid"
                             class="filebrowser hgrid dropbox-folder-picker"></div>
                    </div>

                    <!-- Share -->
                    <div data-bind="visible: currentDisplay() === SHARE && emails().length === 0"
                        class="help-block">
                        <p>No contributors to share with.</p>
                    </div>

                    <div data-bind="visible: currentDisplay() === SHARE && emails().length">
                        <div class="help-block">
                            <p>To share this folder with other Dropbox users on this project, copy
                            the email addresses of the contributors (listed below) into the
                            "Share Folder" dialog on Dropbox.</p>
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
                                class="btn btn-link"><i class="icon-share-alt"></i> Continue to Dropbox...</a>
                        </div>
                    </div>

                    <!-- Queued selection -->
                    <div class="dropbox-confirm-selection"
                        data-bind="visible: currentDisplay() == PICKER && selected()">
                        <form data-bind="submit: submitSettings">

                            <h4 data-bind="if: selected" class="dropbox-confirm-dlg">
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
                    </div><!-- end .dropbox-confirm-selection -->

                </div>
            </div><!-- end col -->
        </div><!-- end row -->
    </div><!-- end .dropbox-settings -->

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr.class: messageClass"></p>
    </div>
</div><!-- end #dropboxScope -->

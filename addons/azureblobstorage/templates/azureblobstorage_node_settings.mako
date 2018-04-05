<div id="azureblobstorageScope" class="scripted">

    <!-- Add credentials modal -->
    <%include file="azureblobstorage_credentials_modal.mako"/>

    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
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
                <a href="#azureblobstorageInputCredentials" data-toggle="modal" class="pull-right text-primary addon-auth">
                    Connect  Account
                </a>
            </span>
        </small>
    </h4>
    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings" data-bind='visible: showSettings'>
        <div class="row">
            <div class="col-md-12">
                <p class="break-word">
                    <strong>Current Container:</strong>
                    <span data-bind="if: folderName">
                        <a data-bind="attr: {href: urls().files}, text: folderName"></a>
                    </span>
                    <span class="text-muted" data-bind="ifnot: folderName">
                        None
                    </span>
                </p>
                <!-- Folder buttons -->
                <div class="form-group" data-bind="visible: userIsOwner() && validCredentials()">
                    <button data-bind="click: togglePicker,
                                       css: {active: currentDisplay() === PICKER}" class="btn btn-primary">
                                       <span data-bind="text: toggleChangeText"></span></button>
                    <button data-bind="visible: userIsOwner() && validCredentials(), click: openCreateContainer" class="btn btn-success" id="newContainer">Create container</button>
                </div>
                <!-- Folder picker -->
                <div class="m-t-sm addon-folderpicker-widget ${addon_short_name}-widget">
                    <p class="text-muted text-center ${addon_short_name}-loading-text" data-bind="visible: loading">
                        Loading containers...</p>
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

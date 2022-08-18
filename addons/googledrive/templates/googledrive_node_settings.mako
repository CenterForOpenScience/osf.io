<div id="${addon_short_name}Scope" class="scripted">
    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        ${addon_full_name}
        <small class="authorized-by">
            <span data-bind="if: nodeHasAuth">
                ${_("authorized by %(ownerName)s") % dict(ownerName='<a data-bind="attr: {href: urls().owner}, text: ownerName"></a>') | n}
                % if not is_registration:
                    <a data-bind="click: deauthorize, visible: validCredentials"
                        class="text-danger pull-right addon-auth">${_("Disconnect Account")}</a>
                % endif
            </span>

             <!-- Import Access Token Button -->
            <span data-bind="if: showImport">
                <a data-bind="click: importAuth" href="#" class="text-primary pull-right addon-auth">
                    ${_("Import Account from Profile")}
                </a>
            </span>

            <!-- Loading Import Text -->
            <span data-bind="if: showLoading">
                <p class="text-muted pull-right addon-auth">
                    ${_("Loading ...")}
                </p>
            </span>

            <!-- Oauth Start Button -->
            <span data-bind="if: showTokenCreateButton">
                <a data-bind="click: connectAccount" class="text-primary pull-right addon-auth">
                    <img
                        src="/static/addons/googledrive/btn_google_signin_normal.png"
                        onmouseover="this.src='/static/addons/googledrive/btn_google_signin_focus.png'"
                        onmouseout="this.src='/static/addons/googledrive/btn_google_signin_normal.png'"
                        onmousedown="this.src='/static/addons/googledrive/btn_google_signin_pressed.png'"
                        onmouseup="this.src='/static/addons/googledrive/btn_google_signin_normal.png'"
                        style="margin-top: -18px;"
                        alt="${_('Connect Account')}"
                    >
                </a>
            </span>
        </small>
    </h4>
    <!-- Settings Pane -->
    <div class="${addon_short_name}-settings" data-bind='visible: showSettings'>
        <div class="row">
            <div class="col-md-12">
                <p class="break-word">
                    <strong>${_("Current Folder:")}</strong>
                    <span data-bind="if: folderName">
                        <a data-bind="attr: {href: urls().files}, text: folderName"></a>
                    </span>
                    <span class="text-muted" data-bind="ifnot: folderName">
                        ${_("None")}
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
                        ${_("Loading folders...")}</p>
                    <div data-bind="visible: currentDisplay() === PICKER">
                        <div id="${addon_short_name}Grid" class="filebrowser ${addon_short_name}-folder-picker"></div>
                    </div>
                    <!-- Queued selection -->
                    <div class="${addon_short_name}-confirm-selection" data-bind="visible: currentDisplay() == PICKER && selected()">
                        <form data-bind="submit: submitSettings">
                            <div class="break-word">
                                <div data-bind="if: selected" class="alert alert-info ${addon_short_name}-confirm-dlg">
                                    ${_("Connect %(folderName)s?") % dict(folderName='<b>&ldquo;<span data-bind="text: selectedFolderName"></span>&rdquo;</b>') | n}
                                </div>
                            </div>
                            <div class="pull-right">
                                <button class="btn btn-default" data-bind="click: cancelSelection">
                                    ${_("Cancel")}
                                </button>
                                <input type="submit" class="btn btn-success" value="${_('Save')}" />
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

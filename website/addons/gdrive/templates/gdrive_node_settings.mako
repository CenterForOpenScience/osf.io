
<div id="driveAddonScope" class="scripted">
<h4 class="addon-title">
    Google Drive
    <small class="authorized-by">
        <span data-bind="if:nodeHasAuth">
            authorized by <a data-bind="attr.href: owner">
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
            <a data-bind="click: createAuth" class="text-primary pull-right addon-auth">
                Create Access Token
            </a>
        </span>
    </small>
    </h4>



    <div id="currentFolder" data-bind="if:showFolders()">
       <p>
        <strong> Current folder:</strong>
        <span data-bind = "text:selectedName, style:{color: selectedName() == 'No folder selected yet !' ? 'red' : 'black'}"> </span>
       </p>

        <div class="btn-group" >
        <button data-bind="click:changeFolder" class="btn btn-sm btn-dropbox"> Change Folder</button>
        </div>

        <!-- Google Drive Treebeard -->
        <p class="text-muted text-center dropbox-loading-text" data-bind="visible: loading">
                    Loading folders...</p>
        <div id="myGdriveGrid"
             class="filebrowser hgrid dropbox-folder-picker">


        </div>

        <!-- Queued selection -->
        <div class="gdrive-confirm-selection"
            data-bind="visible:selected">
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
        </div><!-- end gdrive-confirm-selection -->


    </div>


    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message"></p>
    </div>

</div> <!-- End of driveAddonScope -->


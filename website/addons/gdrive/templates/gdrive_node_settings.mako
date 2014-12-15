
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
        <span data-bind = "text:selectedName"> </span>
       </p>

        <div id="display-permissions">
            <p>
            <select data-bind = "value : selectedFileTypeOption , optionsCaption : 'Choose..'">
                <option value="">Chose...</option>
                <option value="owner">Owned only by Me</option>
                <option value="incoming">Shared by me but not owned by me</option>
                <option value="all">All files</option>
            </select>
            </p>
        </div>

         <div class="btn-group" >
           <button data-bind="click:changeFolder" class="btn btn-sm btn-dropbox"> Change Folder</button>
       </div>
        <div id="myGdriveGrid"
             class="filebrowser hgrid dropbox-folder-picker">

        </div>
    </div>


    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message"></p>
    </div>

</div> <!-- End of driveAddonScope -->


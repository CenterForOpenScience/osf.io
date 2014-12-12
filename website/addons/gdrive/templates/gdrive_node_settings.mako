
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
        <span>sdjbdk/cgdshcj </span>
       </p>

       <div class="btn-group" >
           <button data-bind="click:changeFolder" class="btn btn-sm btn-dropbox"> Change Folder</button>
           <button data-bind="newFolder" class="btn btn-sm btn-dropbox"> Add New Folder</button>
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


##<script>
##    $script(['/static/addons/gdrive/gdriveNodeConfig.js'], function() {
##
##        var url = '${node["api_url"] + "gdrive/config/"}';
##        var drive = new GdriveNodeConfig('#driveAddonScope', url);
##
##    });
##
##</script>
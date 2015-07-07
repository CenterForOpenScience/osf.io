<div id="${addon_short_name}Scope" class="scripted">
	<h4 class="addon-title">
		${addon_full_name}
		<small class="authorized-by">
			<span data-bind="if: nodeHasAuth">
                authorized by <a data-bind="attr.href: urls().owner">
                {{ownerName}}
                </a>
                % if not is_registration:
                    <a data-bind="click: deauthorizeNode" class="text-danger pull-right addon-auth">
                      Deauthorize
                    </a>
                % endif
            </span>
            <span data-bind="if: showImport">
            	<a data-bind="click: importAuth" class="text-primary pull-right addon-auth">
            		Import Account Access
            	</a>
            </span>
            <span data-bind="if: showCreateCredentials">
            	<a data-bind="click connectAccount" class="text-primary pull-right addon-auth">
            		Connect Account
            	</a>
            </span>
        </small>
	</h4>
	<div data-bind="if: showSettings">
		<p>
			<strong>Current {{folderType}}:</strong>
			<span data-bind="ifnot: currentFolder">None</span>
			<a data-bind="if: currentFolder, attr.href: urls().files">
				{{currentFolder}}
			</a>
		</p>
		<div class="btn-group" role="group" data-bind="attr.disabled: creating">
			<button data-bind="if: canChange, click: toggleSelect, css: {active: showSelect}" class="btn btn-sm btn-addon"><i class="icon-edit"></i>Change</button>
			<button data-bind="if: showNewFolder, click: openCreateFolder, attr.disabled: creating" class="btn btn-sm btn-addon" id="newFolder">Create {{folderType}}</button>

		</div>
		<br />
		<div class="row" data-bind="if: showSelect">
			<div class="col-md-6">
				<select class="form-control" id="folder" name="folder" data-bind="value: selectedFolder, attr.disabled: !loadedFolderList(), options: folderList"></select>
			</div>
			<div class="col-md-2">
				<button data-bind="click: selectFolder, attr.disabled: !allowSelectFolder()" class="btn btn-primary">Submit</button>
			</div>
		</div>
	</div>
	<div class="help-block">
		<p data-bind="html: message, attr.class: messageClass"></p>
	</div>
</div>

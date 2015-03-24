<div id="githubScope" class="scripted">
    <h4 class="addon-title">
        Github
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
                  Import Access Token
                </a>
            </span>
        </small>            
    </h4>
    <div data-bind="if: showSettings">
        <p>
            <strong>Current Repo:</strong>
            <span data-bind="text: currentRepo"></span>
        </p>
        <div class="row"
             data-bind="attr.disabled: creating">
          <div class="col-md-1" data-bind="if: canChange">
            <button data-bind="click: toggleSelect,
                               css: {active: showSelect}" class="btn btn-sm btn-addon"><i class="icon-edit"></i> Change</button>
          </div>
          <div class="col-md-1" data-bind="if: showNewRepo">
            <button data-bind="click: openCreateRepo,
                               attr.disabled: creating" class="btn btn-sm btn-addon" id="newRepo">Create Repo</button>
          </div>
        </div>
        <br />
        <div class="row" data-bind="if: showSelect">
          <div class="col-md-6">
            <select class="form-control" id="github_repo" name="github_repo" 
                    data-bind="value: selectedRepo,
                               attr.disabled: !loadedRepoList(),
                               options: repoList"> </select>
          </div>
          <div class="col-md-2">
            <button data-bind="click: selectRepo,
                               attr.disabled: !allowSelectRepo()"
                    class="btn btn-primary">
              Submit
            </button> 
          </div>         
        </div>          
    </div>
    <div data-bind="if: showCreateCredentials">
      <div class="form-group">
        <label for="githubAddon">Access Key</label>
        <input data-bind="value: accessKey" class="form-control" id="access_key" name="access_key" />
      </div>
      <div class="form-group">
        <label for="githubAddon">Secret Key</label>
        <input data-bind="value: secretKey" type="password" class="form-control" id="secret_key" name="secret_key" />
      </div>
      <button data-bind="click: createCredentials,
                         attr.disabled: creatingCredentials" class="btn btn-primary addon-settings-submit">
        Submit
      </button>
    </div>
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr.class: messageClass"></p>
    </div>
</div>
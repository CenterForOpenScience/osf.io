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
             <span data-bind="if: showCreateCredentials">
                <a data-bind="click: connectAccount" id="githubAddKey" class="text-primary pull-right addon-auth">
                    Create Access Token
                </a>
             </span>
        </small>

    </h4>
    <div data-bind="if: showSettings">
        <p>
            <strong>Current Repo:</strong>

            <a data-bind="attr.href: urls().files">
                {{currentRepo}}
            </a>
        </p>
        <div class="btn-group" role="group" data-bind="attr.disabled: creating">

            <button data-bind="if: canChange, click: toggleSelect,
                               css: {active: showSelect}" class="btn btn-sm btn-addon"><i class="icon-edit"></i> Change</button>

            <button data-bind="if: showNewRepo, click: openCreateRepo,
                               attr.disabled: creating" class="btn btn-sm btn-addon" id="newRepo">Create Repo</button>
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
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr.class: messageClass"></p>
    </div>

</div>
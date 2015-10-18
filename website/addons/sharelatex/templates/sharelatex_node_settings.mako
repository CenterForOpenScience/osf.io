 <div id="sharelatexScope" class="scripted">
    <h4 class="addon-title">
        <img class="addon-icon" src="${addon_icon_url}"></img>
        ShareLatex
        <small class="authorized-by">
            <span data-bind="if: nodeHasAuth">
                authorized by <a data-bind="attr.href: urls().owner">
                {{ownerName}}
                </a>
                % if not is_registration:
                    <a data-bind="click: deauthorizeNode" class="text-danger pull-right addon-auth">
                      Disconnect Account
                    </a>
                % endif
            </span>
            <span data-bind="if: showImport">
                <a data-bind="click: importAuth" class="text-primary pull-right addon-auth">
                  Import Account from Profile
                </a>
            </span>
        </small>
    </h4>
    <div data-bind="if: showSettings">
      <div class="row">
      <div class="col-md-12">
        <p><strong>Current Project:</strong></p>
        <div class="row">

          <div class="form-group col-md-8">
            <select class="form-control" id="sharelatex_project" name="sharelatex_project"
                    data-bind="value: selectedBucket,
                               attr.disabled: !loadedBucketList(),
                               options: projectList,
                               optionsText: function(item) {
                                   return item.name;
                               },
                               optionsValue: function(item) {
                                   return item.id;
                               },
                               optionsCaption: 'Choose...'">
                               </select>
          </div>
          <div class="col-md-2">
            <button data-bind="click: selectBucket,
                               attr.disabled: !allowSelectBucket(),
                               text: saveButtonText"
                    class="btn btn-success">
              Save
            </button>
          </div>
        </div>
      </div>
      </div>
    </div>
    <div data-bind="if: showCreateCredentials">
      <div class="form-group">
        <label for="sharelatexAddon">URL</label>
        <input data-bind="value: sharelatexUrl" class="form-control" id="sharelatex_url" name="sharelatex_url" />
      </div>
      <div class="form-group">
        <label for="sharelatexAddon">Auth Token</label>
        <input data-bind="value: authToken" type="text" class="form-control" id="auth_token" name="auth_token" />
      </div>
      <button data-bind="click: createCredentials,
                         attr.disabled: creatingCredentials" class="btn btn-success addon-settings-submit">
        Save
      </button>
    </div>
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr.class: messageClass"></p>
    </div>
</div>

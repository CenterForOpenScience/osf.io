 <div id="s3Scope" class="scripted">
    <h4 class="addon-title">
        <img class="addon-icon" src="${addon_icon_url}"></img>
        Amazon S3
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
      <div class="row">
      <div class="col-md-12">
        <p>
          <strong>Current Bucket:</strong>
          <span data-bind="ifnot: currentBucket">
            None
          </span>
          <a data-bind="if: currentBucket, attr.href: urls().files">
            {{currentBucket}}
          </a>
        </p>
        <div class="btn-group"
             data-bind="attr.disabled: creating">
          <button data-bind="visible: canChange, click: toggleSelect,
                             css: {active: showSelect}" class="btn btn-sm btn-addon"><i class="icon-edit"></i> Change</button>
          <button data-bind="visible: showNewBucket, click: openCreateBucket,
                             attr.disabled: creating" class="btn btn-sm btn-addon" id="newBucket">Create Bucket</button>
        </div>
        <br />
        <br />
        <div class="row" data-bind="if: showSelect">
          <div class="col-md-8">
            <select class="form-control" id="s3_bucket" name="s3_bucket"
                    data-bind="value: selectedBucket,
                               attr.disabled: !loadedBucketList(),
                               options: bucketList"> </select>
          </div>
          <div class="col-md-2">
            <button data-bind="click: selectBucket,
                               attr.disabled: !allowSelectBucket()"
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
        <label for="s3Addon">Access Key</label>
        <input data-bind="value: accessKey" class="form-control" id="access_key" name="access_key" />
      </div>
      <div class="form-group">
        <label for="s3Addon">Secret Key</label>
        <input data-bind="value: secretKey" type="password" class="form-control" id="secret_key" name="secret_key" />
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

<div id="s3Scope" class="scripted">
    <h4 class="addon-title">
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
        <p>
            <strong>Current Bucket:</strong>
            <span data-bind="text: currentBucket"></span>
        </p>
        <div class="row">
          <div class="col-md-1" data-bind="if: canChange">
            <button data-bind="click: toggleSelect,
                               css: {active: showSelect}" class="btn btn-sm btn-addon"><i class="icon-edit"></i> Change</button>
          </div>
          <div class="col-md-1" data-bind="if: showNewBucket">
            <button data-bind="click: openCreateBucket,
                               attr.disabled: creating" class="btn btn-sm btn-addon" id="newBucket">Create Bucket</button>
          </div>
        </div>
        <br />
        <div class="row" data-bind="if: showSelect">     
          <div class="col-md-6">
            <select class="form-control" id="s3_bucket" name="s3_bucket" data-bind="value: selectedBucket, attr.diabled: disableSettings, options: bucketList"> </select>
          </div>
          <div class="col-md-2">
            <button data-bind="click: selectBucket,
                               attr.disabled: loading" class="btn btn-primary">
              Submit
            </button> 
          </div>         
        </div>          

        <div data-bind="if: showCreateCredentials">
          <div class="form-group">
            <label for="s3Addon">Access Key</label>
            <input data-bind="value: accessKey" class="form-control" id="access_key" name="access_key" />
          </div>
          <div class="form-group">
            <label for="s3Addon">Secret Key</label>
            <input data-bind="value: password" type="password" class="form-control" id="secret_key" name="secret_key" />
          </div>
          <button data-bind="click: createCredentials" class="btn btn-success btn-addon addon-settings-submit">
            Submit
          </button>
        </div>
    </div>
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr.class: messageClass"></p>
    </div>
</div>

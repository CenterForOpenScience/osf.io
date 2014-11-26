<form role="form" style="display: none" id="s3AddonNodeScope" data-addon="s3">
<!-- <pre data-bind="text: ko.toJSON($data, null, 2)"></pre> -->
    <div>
        <h4 class="addon-title">
            Amazon S3

            <small class="authorized-by">
                <!-- ko if: nodeHasAuth -->
                    authorized by
                    <a data-bind="attr: {href: ownerURL}, text: ownerName" target="_blank"></a>
                    <!-- ko ifnot: isRegistration -->
                        <a data-bind="click: s3RemoveToken" class="text-danger pull-right addon-auth">Deauthorize</a>
                    <!-- /ko -->
                <!-- /ko -->
                <!-- ko ifnot: nodeHasAuth -->
                    <!-- ko if: userHasAuth -->
                        <a data-bind="click: s3ImportToken" class="text-primary pull-right addon-auth">Import Credentials</a>
                    <!-- /ko -->
                <!-- /ko -->
            </small>

        </h4>
    </div>

    <!-- ko if: bucketList -->
        <div class="form-group">
            <p> <strong>Current Bucket:</strong></p>
            <div class="row">       
                <!-- ko if: userHasAuth -->
                    <!-- ko if: userIsOwner -->
                        <!-- ko ifnot: isRegistration -->
                            <div class="col-md-6">
                                <select class="form-control" id="s3_bucket" name="s3_bucket" data-bind="options: bucketList, selectedOptions: selectedBucket"></select>
                            </div>
                            <div class="col-md-6">
                                <a class="btn btn-default" data-bind="click: makeNewBucket">Create Bucket</a>

                                <button class="btn btn-primary addon-settings-submit pull-right" data-bind="click: submitSettingsAuth">
                                    Submit
                                </button>
                            </div>
                        <!-- /ko -->
                    <!-- /ko -->
                <!-- /ko -->
            </div>
        </div>
    <!-- /ko -->

    <!-- ko if: nodeHasAuth -->
        <!-- ko ifnot: bucketList -->
        <div>
            <i class="icon-spinner icon-large icon-spin"></i>
            <span class="text-info">
                S3 access keys loading. Please wait a moment and refresh the page.
            </span>
        </div>
        <!-- /ko -->
    <!-- /ko -->

    <!-- ko ifnot: nodeHasAuth -->
        <!-- ko ifnot: userHasAuth -->
        <div class="form-group">
            <label for="s3Addon">Access Key</label>
            <input class="form-control" id="access_key" name="access_key" data-bind="textInput: accessKey"/>
        </div>
        <div class="form-group">
            <label for="s3Addon">Secret Key</label>
            <input type="password" class="form-control" id="secret_key" name="secret_key" data-bind="textInput: secretKey"/>
        </div>

        <button class="btn btn-success addon-settings-submit" data-bind="click: submitSettingsNoAuth">
            Submit
        </button>
        <!-- /ko -->
    <!-- /ko -->

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr.class: messageClass"></p>
    </div>

</form>
<script>
    $script(['/static/addons/s3/s3-node-settings.js']);
    $script.ready('s3NodeSettings', function() {
        var url = '${node["api_url"] + "s3/"}';
        var s3 = new s3NodeSettings('#s3AddonNodeScope', url);
    });
</script>

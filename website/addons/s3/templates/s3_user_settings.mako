
<form role="form" style="display: none" id="s3AddonUserScope" data-addon="s3">
    <span data-owner="user"></span>

    <div>
        <h4 class="addon-title">
            Amazon S3

            <small class="authorized-by" data-bind="if: userHasAuth()">
                    authorized
                    <a class="text-danger pull-right addon-auth" data-bind="click: s3RemoveAccess">Delete Credentials</a>
            </small>

        </h4>
    </div>

        <div class="form-group" data-bind="ifnot: userHasAuth">
            <label >Access Key</label>
            <input class="form-control" data-bind="textInput: accessKey"/>
        </div>
        <div class="form-group" data-bind="ifnot: userHasAuth">
            <label >Secret Key</label>
            <input type="password" class="form-control" data-bind="textInput: secretKey"/>
        </div>
        <!-- ko ifnot: userHasAuth() -->
            <button class="btn btn-success addon-settings-submit" data-bind="click: submitSettings">
            Submit
            </button>
        <!-- /ko -->

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr.class: messageClass"></p>
    </div>

</form>

<%include file="profile/addon_permissions.mako" />
<script>
    $script(['/static/addons/s3/s3-user-settings.js']);
    $script.ready('s3UserSettings', function() {
        var s3 = new s3UserSettings('#s3AddonUserScope');
    });
</script>
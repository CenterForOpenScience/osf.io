<%inherit file="project/addon/user_settings.mako" />

<div class="form-group">
    <label for="s3Addon">Access Key</label>
    <input class="form-control" id="access_key" name="access_key" value="${access_key}" ${'disabled' if disabled else ''} />
</div>
<div class="form-group">
    <label for="s3Addon">Secret Key</label>
    <input type="password" class="form-control" id="secret_key" name="secret_key" value="${secret_key}" ${'disabled' if disabled else ''} />
</div>
## if use has other else delete key
<%def name="submit_btn()">
    <button class="btn btn-success addon-settings-submit">
        Submit
    </button>
</%def>
##TODO create a remove access key

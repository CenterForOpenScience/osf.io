<%inherit file="project/addon/settings.mako" />

<div class="form-group">
    <label for="githubRepo">Access Key</label>
    <input class="form-control" id="access_key" name="access_key" value="${access_key}" ${'disabled' if disabled else ''} />
</div>
<div class="form-group">
    <label for="githubRepo">Secret Key</label>
    <input class="form-control" id="secret_key" name="secret_key" value="${secret_key}" ${'disabled' if disabled else ''} />
</div>

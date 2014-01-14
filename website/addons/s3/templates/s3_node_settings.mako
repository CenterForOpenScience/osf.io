<%inherit file="project/addon/settings.mako" />

<div class="form-group">
    <label for="githubRepo">Bucket Name</label>
    <input class="form-control" id="s3_bucket" name="s3_bucket" value="${s3_bucket}" ${'disabled' if disabled else ''} />
</div>
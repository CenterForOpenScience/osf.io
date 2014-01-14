<%inherit file="project/addon/settings.mako" />

<div class="form-group">
	%if node_auth:

    		<label for="s3Addon">Access Key</label>
    		<input class="form-control" id="secret_key" name="secret_key" value="${access_key}" disabled />
    		 <br>
        	<a id="githubDelKey" class="btn btn-danger">Delete Access Key</a>
	%else:
        <a id="s3getKey" class="btn btn-primary  ${'' if user_has_auth else 'disabled'}">
        	Create Access Key
        </a>

    %endif
</div>

<br>

<div class="form-group">
    <label for="githubRepo">Bucket Name</label>
    <input class="form-control" id="s3_bucket" name="s3_bucket" value="${s3_bucket}" ${'disabled' if not node_auth else ''} />
</div>


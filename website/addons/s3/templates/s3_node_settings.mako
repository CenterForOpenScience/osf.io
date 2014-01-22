<%inherit file="project/addon/settings.mako" />

%if user_has_auth:
    <div class="form-group">
        <label for="s3_bucket">Bucket Name</label>
        <input class="form-control" id="s3_bucket" name="s3_bucket" value="${s3_bucket}" ${'disabled' if disabled else ''}/>
    </div>
%else:
    Amazon Simple Storage Service add-on is not configured properly.
    <br>
    Configure this add-on on the <a href="/settings/">settings</a> page, or click <a class="widget-disable" href="${node['api_url']}s3/settings/disable/">here</a> to disable it.
    <br>

    <script>
        $(document).ready(function() {
            $("#addon-settings-submit").attr('disabled','disabled');
        });
    </script>

%endif
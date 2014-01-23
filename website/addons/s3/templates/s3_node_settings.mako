<%inherit file="project/addon/node_settings.mako" />

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

%endif


<%def name="submit_btn()">
    %if user_has_auth and node_auth:
        <button class="btn btn-danger">
            Remove Access
        </button>

    %elif user_has_auth:
        <button class="btn btn-success addon-settings-submit">
        Submit
        </button>
    %else:

    %endif
</%def>

##TODO this should be in an if and in an external js file
##TODO Fixe me? whydoInotwork
%if user_has_auth:
    <%def name="on_submit()">
        <script type="text/javascript">
         $(document).ready(function() {
            $('#${addon_short_name}').on('submit', function() {
                alert("called");
                $.ajax({
                    url: nodeApiUrl + addon + '/settings/delete/`',
                    type: 'POST'
                }).success(function() {
                    msgElm.text('Access key removed')
                        .removeClass('text-danger').addClass('text-success')
                        .fadeOut(100).fadeIn();
                }).fail(function(xhr) {
                    var message = 'Error: Access key not removed';
                    msgElm.text(message)
                        .removeClass('text-success').addClass('text-danger')
                        .fadeOut(100).fadeIn();
                });
            });
        });
        </script>
    </%def>
%endif
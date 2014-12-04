<div class='addon-config-error'>
    ${full_name} add-on is not configured properly.
    ## Only show settings links if contributor
    % if user['is_contributor']:
        Configure this add-on on the <a href="${node['url']}settings/">settings</a> page,
        or click <a class="widget-disable">here</a> to disable it.
    % endif
</div>

<script>
    $(document).ready(function() {
        $(".widget-disable").click(function() {
        var req = $.osf.postJSON('${node['api_url']}${short_name | js_str}/settings/disable/', {});

            req.done(function() {
                location.reload();
            })

            req.fail(function() {
                bootbox.alert('Unable to disable ${full_name | js_str}');
            })
        });
    });
</script>

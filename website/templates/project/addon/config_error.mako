<div class='addon-config-error'>
    ${full_name} add-on is not configured properly.
    ## Only show settings links if contributor
    % if user['is_contributor']:
        Configure this add-on on the <a href="${node['url']}settings/">settings</a> page,
        or click <a class="widget-disable" href="${node['api_url']}${short_name}/settings/disable/">here</a> to disable it.
    % endif
</div>

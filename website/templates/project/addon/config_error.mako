<div class='addon-config-error p-sm'>
    ${full_name} add-on is not configured properly.
    % if user['is_contributor']:
      Configure this add-on on the <a href="${node['url']}settings/">settings</a> page.
    % endif
</div>

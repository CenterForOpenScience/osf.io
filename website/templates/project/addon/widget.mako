% if complete or 'write' in user['permissions']:
    <div class="panel panel-default" name="${short_name}">
        <div class="panel-heading clearfix">
            <h3 class="panel-title">${full_name}</h3>
            <div class="pull-right">
                % if has_page:
                   <a href="${node['url']}${short_name}/">  <i class="fa fa-external-link"></i> </a>
               % endif
            </div>
        </div>
        % if complete:
            <div class="panel-body">
                ${self.body()}
            </div>
        % else:
            <div class='addon-config-error p-sm'>
                ${full_name} add-on is not configured properly.
                % if user['is_contributor']:
                    Configure this add-on on the <a href="${node['url']}settings/">settings</a> page.
                % endif
            </div>

        % endif
    </div>
% endif

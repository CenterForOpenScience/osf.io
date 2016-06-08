% if complete or 'write' in user['permissions']:
    <div class="panel panel-default" name="${short_name}" id="div">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">${full_name}</h3>
                <div class="pull-right">
                    % if has_page:
                       <a href="${node['url']}${short_name}/">  <i class="fa fa-external-link"></i> </a>
                   % endif

                </div>
            </div>
    % else:
        <div>
    % endif

    % if complete:

        <div class="panel-body">
            ${self.body()}
        </div>

    % elif not complete and 'write' in user['permissions']:

        <div mod-meta='{
                "tpl": "project/addon/config_error.mako",
                "kwargs": {
                    "short_name": "${short_name}",
                    "full_name": "${full_name}"
                }
            }'></div>

    % endif

</div>

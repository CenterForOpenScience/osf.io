<div class="panel panel-default" name="${short_name}">

            <div class="panel-header clearfix">
                <h4 class="panel-title">${full_name}</h4>
                <div class="pull-right">
                    % if has_page:
                       <a href="${node['url']}${short_name}/" class="btn">  <i class="fa fa-external-link"></i> </a>
                   % endif

                </div>
            </div>

    % if complete:

        <div class="panel-body">
            ${self.body()}
        </div>

    % else:

        <div mod-meta='{
                "tpl": "project/addon/config_error.mako",
                "kwargs": {
                    "short_name": "${short_name}",
                    "full_name": "${full_name}"
                }
            }'></div>

    % endif

</div>

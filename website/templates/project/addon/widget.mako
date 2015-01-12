<div class="addon-widget" name="${short_name}">

            <div class="addon-widget-header clearfix"> 
                <h4>${full_name}</h4>
                <div class="pull-right">
                    % if has_page:
                       <a href="${node['url']}${short_name}/" class="btn">  <i class="icon icon-external-link"></i> </a>
                   % endif
                       <span class="btn">  <i class="icon icon-angle-up"></i> </span>

                </div>
            </div>

    % if complete:

        <div class="addon-widget-body">
            ${self.body()}
        </div>

        % if has_page and more:
            <div>
                <a href="${node['url']}${short_name}/">More</a>
            </div>
        % endif

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

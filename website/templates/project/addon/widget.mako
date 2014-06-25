<div class="addon-widget" name="${short_name}">

    <h3 class="addon-widget-header">
        % if has_page:
            <a href="${node['url']}${short_name}/">${full_name}</a>
        % else:
            <span>${full_name}</span>
        % endif
    </h3>

    % if complete:

        <div class="addon-content">
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

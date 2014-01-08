<div class="addon-widget">

    <h3 class="addon-widget-header">
        % if help:
            <span data-toggle="tooltip" title="${help}">
                <i class="icon-question-sign"></i>
            </span>
        % endif
        <span>${title}</span>
    </h3>

    % if complete:

        <div class="addon-content">
            ${self.body()}
        </div>

        % if page and more:
            <div>
                <a href="${node['url']}${name}/">More</a>
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

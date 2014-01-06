<%namespace file="config_error.mako" import="config_error" />

<%def name="widget(name, title, help, page, content)">

    <div class="addon-widget">

        <h3 class="addon-widget-header">
            % if help:
                <span data-toggle="tooltip" title="${help}">
                    <i class="icon-question-sign"></i>
                </span>
            % endif
            <span>${title}</span>
        </h3>

        <div class="addon-content">

            % if content:
                ${content}
            % else:
                ${config_error(name, title)}
            % endif

        </div>

        % if page:
            <div>
                <a href="${node['url']}${name}/">More</a>
            </div>
        % endif

    </div>

</%def>

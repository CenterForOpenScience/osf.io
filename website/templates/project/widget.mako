<%def name="widget(name, title, help, page, content)">

    <h3>
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
            <div class="addon-not-configured">
                ${title} addon not configured:
                Configure this addon on the <a href="/${node['url']}/settings/">settings</a> page,
                or click <a class="widget-disable" href="{url}settings/${name}/disable/">here</a> to disable it.
            </div>
        % endif

    </div>

    % if page:
        <div>
            <a href="${node['url']}${name}/">More</a>
        </div>
    % endif

</%def>
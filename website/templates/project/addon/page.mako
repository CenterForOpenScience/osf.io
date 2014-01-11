<%inherit file="../../base.mako"/>

<%def name="content()">

<div mod-meta='{
        "tpl": "project/project_header.mako",
        "replace": true
    }'></div>
    <span></span>

% if complete:

    <div class="addon-content">
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

</%def>

<%def name="stylesheets()">

    ${parent.stylesheets()}

    % for style in addon_page_css or []:
        <link rel="stylesheet" href="${style}" />
    % endfor

</%def>

<%def name="javascript_bottom()">

    ${parent.javascript_bottom()}

    % for script in addon_page_js or []:
        <script type="text/javascript" src="${script}"></script>
    % endfor

</%def>

<%inherit file="../../base.mako"/>

<%def name="content()">

<div mod-meta='{
        "tpl": "project/project_header.mako",
        "replace": true
    }'></div>
    <span></span>

<h4>
    % if capabilities:
        <span class="addon-capabilities">
            <i class="icon-question-sign"></i>
        </span>
    % endif
    ${full_name} Add-on
</h4>

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

<script id="capabilities" type="text/html">${addon_capabilities}</script>

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

    <script type="text/javascript">
        // Show capabilities modal on addon widget help
        $('.addon-capabilities').on('click', function() {
            bootbox.alert($('#capabilities').html());
        });
    </script>

</%def>

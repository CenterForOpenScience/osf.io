<%inherit file="../../base.mako"/>

<%def name="page()"></%def>

<%def name="content()">

<div mod-meta='{
        "tpl": "project/project_header.mako",
        "replace": true
    }'></div>
    <span></span>

${self.page()}

</%def>

<%def name="stylesheets()">

    ${parent.stylesheets()}

    % for style in addon_page_css:
        <link rel="stylesheet" href="${style}" />
    % endfor

</%def>

<%def name="javascript_bottom()">

    ${parent.javascript_bottom()}

    % for script in addon_page_js:
        <script type="text/javascript" src="${script}"></script>
    % endfor

</%def>

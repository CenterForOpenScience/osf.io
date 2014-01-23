<%inherit file="settings.mako" />

        ${next.body()}

        % if node and not node['is_registration']:
            ${next.submit_btn()}
        % endif


<%def name="submit_btn()">
    <button class="btn btn-success addon-settings-submit">
        Submit
    </button>
</%def>


##Inheritance gimmick. There does not seem a to be a better solution
<%def name="submit()">
    ${next.on_submit()}
</%def>

<%def name="on_submit()">
    ${parent.submit()}
</%def>
<%inherit file="settings.mako" />

        ${next.body()}

        % if node and not node['is_registration']:
            ${self.submit_btn()}
        % endif


<%def name="submit_btn()">
    <button class="btn btn-success addon-settings-submit">
        Submit
    </button>
</%def>
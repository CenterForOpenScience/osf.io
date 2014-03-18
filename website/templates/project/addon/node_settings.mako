<%inherit file="settings.mako" />

<span data-owner="node"></span>

${self.body()}

% if node and not node['is_registration']:
    ${self.submit_btn()}
% endif

${self.on_submit()}

<%def name="submit_btn()">
    <button class="btn btn-success addon-settings-submit">
        Submit
    </button>
</%def>

<%def name="on_submit()">
    <script type="text/javascript">
        $(document).ready(function() {
            $('#addonSettings${addon_short_name.capitalize()}').on('submit', AddonHelper.onSubmitSettings);
        });
    </script>
</%def>

<%def name="title()">
    <h4>${addon_full_name}</h4>
</%def>

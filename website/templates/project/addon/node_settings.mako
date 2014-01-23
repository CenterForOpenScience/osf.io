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


${next.on_submit()}

<%def name="on_submit()">
    <script type="text/javascript">
        $(document).ready(function() {
            $('#${addon_short_name}').on('submit', on_submit_node);
        });
    </script>
</%def>
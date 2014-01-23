<%inherit file="settings.mako" />

        ${self.body()}

        ${self.submit_btn()}

<%def name="submit_btn()">
</%def>

${next.submit()}

<%def name="submit()">
    <script type="text/javascript">
        $(document).ready(function() {
            $('#${addon_short_name}').on('submit', on_submit_user);
        });
    </script>
</%def>
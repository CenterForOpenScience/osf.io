<%inherit file="settings.mako" />

        ${self.body()}

        ${self.submit_btn()}

<%def name="submit_btn()">
</%def>

${next.on_submit()}

<%def name="on_submit()">
    <script type="text/javascript">
        $(document).ready(function() {
            $('#${addon_short_name}').on('submit', on_submit_user);
        });
    </script>
</%def>
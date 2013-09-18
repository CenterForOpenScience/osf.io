<%def name="render_key_history(key, route)">

    <h2>Key: ${key._id} | ${key.label}</h2>

    <h3>Revision history</h3>
    <%namespace file="_print_logs.mako" import="print_logs" />
    ${print_logs(reversed(key.nodelog__created), n=5)}

    <div>
        <a id="revoke_key" data-key="${key._id}">Revoke key</a>
    </div>

    <script type="text/javascript">
        $('#remove_key').on('click', function() {
            $.post(
                '/api/v1${route}/revoke_key/',
                {key : $(this).attr('data-key')},
                function() {
                    window.location = '${route}';
                }
            );
        });
    </script>

</%def>
<%def name="render_keys(container, route)">

    <div>
        <h2>Keys</h2>
        <form id="create_key" class="form-inline" action="${route}/create_key/" method="POST">
            <input name="label" placeholder="Key label..." />
            <button class="btn" type="submit">Create key</button>
        </form>
        % for key in container.api_keys:
            <div>
                <div>${key._id} | ${key.label}</div>
                <div>
                    <a href="${route}/key_history/${key._id}" class="key_history" data-key="${key._id}">View history</a>
                    <a class="remove_key" data-key="${key._id}">Revoke key</a>
                </div>
            </div>
        % endfor
    </div>

    <script type="text/javascript">
        $('#create_key').on('submit', function() {
            $.post(
                '${route}/create_key/',
                $(this).serialize(),
                function() {
                    window.location.reload();
                }
            );
            return false;
        });
        $('.remove_key').on('click', function() {
            $.post(
                '${route}/remove_key/',
                {key : $(this).attr('data-key')},
                function() {
                    window.location.reload();
                }
            );
        });
    </script>

</%def>
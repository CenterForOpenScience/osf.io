## TODO: Is this used anywhere?

<h2>Key: ${key} | ${label}</h2>

<h3>Revision history</h3>

% for log in logs:
    <div mod-meta='{
            "tpl": "util/render_log.mako",
            "uri": "/api/v1/log/${log["lid"]}/",
            "replace": true
        }'></div>
% endfor

<div>
    <a id="revoke_key" data-key="${key}">Revoke key</a>
</div>

<script type="text/javascript">
    $('#revoke_key').on('click', function() {
        $.post(
            '${route}/revoke_key/',
            {key : $(this).attr('data-key')},
            function() {
                window.location = '${route}';
            }
        );
    });
</script>

<dl class="dl-horizontal activity-log">
% for log in logs:
    <div mod-meta='{
            "tpl": "util/render_log.mako",
            "uri": "/api/v1/log/${log}/",
            "error": "Log unavailable (private component)",
            "replace": true
        }'></div>
% endfor
</dl>

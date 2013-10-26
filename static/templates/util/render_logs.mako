<dl class="dl-horizontal activity-log">
% for log in logs:
    <div mod-meta='{
            "tpl": "util/render_log.mako",
            "uri": "/api/v1/log/${log}/",
            "error": "<div>Log unavailable (private component)</div>",
            "replace": true
        }'></div>
% endfor
</dl>

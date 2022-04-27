% if addons:
    <script type="text/javascript">
    % for addon in addons_enabled:
        window.contextVars = $.extend(true, {}, window.contextVars, {
            '${addon}AddonEnabled': true,
        });
    % endfor
    </script>
% endif

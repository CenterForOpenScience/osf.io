<script type="text/javascript">
window.contextVars = $.extend(true, {}, window.contextVars, {
    ${short_name}: {
        folder_id: '${list_id | js_str}'
    }
});

</script>
<div class="citation-picker">
    <input id="${short_name}StyleSelect" type="hidden" />
</div>
<div id="${short_name}Widget" class="citation-widget">
        <div class="spinner-loading-wrapper">
            <div class="logo-spin text-center"><img src="/static/img/logo_spin.png" alt="loader"> </div>
            <p class="m-t-sm fg-load-message"> Loading citations...</p>
        </div>
</div>
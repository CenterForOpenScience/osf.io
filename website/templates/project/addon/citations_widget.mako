<script type="text/javascript">
window.contextVars = $.extend(true, {}, window.contextVars, {
    ${short_name | sjson , n }: {
        folder_id: ${list_id | sjson, n }
    }
});
</script>
<div class="citation-picker">
    <input id="${short_name}StyleSelect" type="hidden" />
</div>
<div id="${short_name}Widget" class="citation-widget">
    <div class="spinner-loading-wrapper">
        <div class="logo-spin logo-lg"></div>
        <p class="m-t-sm fg-load-message"> Loading citations...</p>
    </div>
</div>

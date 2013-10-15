<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

<div class="col-md-9">
    ${content}
</div>

<div class="col-md-3">
    <div mod-meta='{
            "tpl": "project/wiki/status.mako",
            "replace": true
        }'></div>
    <div mod-meta='{
            "tpl": "project/wiki/nav.mako",
            "replace": true
        }'></div>

    <div mod-meta='{
            "tpl": "project/wiki/toc.mako",
            "replace": true
        }'></div>

</div>


<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>

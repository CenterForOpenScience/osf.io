<%inherit file="base.mako"/>
<%def name="title()">Settings</%def>
<%def name="content()">
<div mod-meta='{"tpl": "include/subnav.mako", "replace": true}'></div>
<h2 class="page-header">Account Settings</h2>


<div class="row">
    <div class="col-md-6">
        <div class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">Merge Accounts</h3></div>
            <div class="panel-body">
                <a href="/user/merge/">Merge with duplicate account</a>
            </div>
            </div>
    </div>
</div>

##<div mod-meta='{
##        "tpl": "util/render_keys.mako",
##        "uri": "/api/v1/settings/keys/",
##        "replace": true,
##        "kwargs" : {
##            "route": "/settings/"}
##        }'></div>

</%def>

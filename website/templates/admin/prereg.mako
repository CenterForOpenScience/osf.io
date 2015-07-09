<%inherit file="base.mako"/>


<%def name="content()">
<div class="container">
    <div class="row">
        <H1 class="col-md-12">Pre-Registration Prize Admin View - Overview</H1>
    </div>
    <div class="row">
        <div class="col-md-2"><h5>Submission Title</h5></div>
        <div class="col-md-1"><h5>Name</h5></div>
        <div class="col-md-2"><h5>Email</h5></div>
        <div class="col-md-1"><h5>Begun</h5></div>
        <div class="col-md-1"><h5>Submitted</h5></div>
        <div class="col-md-1"><h5>Comments sent?</h5></div>
        <div class="col-md-1"><h5>Approved?</h5></div>
        <div class="col-md-1"><h5>Registered?</h5></div>
        <div class="col-md-1"><h5>Proof of pub?</h5></div>
        <div class="col-md-1"><h5>Payment sent?</h5></div>
    </div>
    <div id="overview">
        <div class="row" id="prereg-row">
            <span data-bind="foreach: drafts">
            	<%include file="admin/prereg-rows.mako" />
            </span>
        </div>
    </div>
</div>
</%def>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}

<script src=${"/static/public/js/prereg-admin-page.js" | webpack_asset}></script>
</%def>

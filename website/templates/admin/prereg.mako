<%inherit file="base.mako"/>


<%def name="content()">
<div class="container">
    <div class="row">
        <H1 class="col-md-12">Pre-Registration Prize Admin View - Overview</H1>
    </div>
    <div class="row">
        <div class="col-md-2 row-title"><a id="submission_title">Submission Title</a></div>
        <div class="col-md-1 row-title"><a id="name">Name</a></div>
        <div class="col-md-2 row-title"><a id="email">Email</a></div>
        <div class="col-md-1 row-title"><a id="begun">Begun</a></div>
        <div class="col-md-1 row-title"><a id="submitted">Submitted</a></div>
        <div class="col-md-1 row-title"><a id="comments_sent">Comments sent?</a></div>
        <div class="col-md-1 row-title"><a id="approved">Approved?</a></div>
        <div class="col-md-1 row-title"><a id="registered">Registered?</a></div>
        <div class="col-md-1 row-title"><a id="proof_of_pub">Proof of pub?</a></div>
        <div class="col-md-1 row-title"><a id="payment_sent">Payment sent?</a></div>
    </div>
    <div id="overview">
        <div class="row scripted" id="prereg-row">
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

<%inherit file="base.mako"/>


<%def name="content()">
<div class="container">
    <div class="row">
        <H1 class="col-md-12">Pre-Registration Prize Admin View - Overview</H1>
    </div>
    <div class="row">
        <div class="col-md-1 row-title"><a id="registration_metadata.q1.value">Submission Title</a></div>
        <div class="col-md-1 row-title"><a id="initiator.fullname">Name</a></div>
        <div class="col-md-1 row-title"><a id="initiator.username">Email</a></div>
        <div class="col-md-1 row-title"><a id="initiated">Begun</a></div>
        <div class="col-md-1 row-title"><a id="updated">Submitted</a></div>
        <div class="col-md-1 row-title"><a id="comments_sent">Comments Sent</a></div>
        <div class="col-md-1 row-title"><a id="new_comments">New Comments</a></div>
        <div class="col-md-1 row-title"><a id="approved">Approved</a></div>
        <div class="col-md-1 row-title"><a id="registered">Registered</a></div>
        <div class="col-md-1 row-title"><a id="proof_of_pub">Proof of Publication</a></div>
        <div class="col-md-1 row-title"><a id="payment_sent">Payment Sent</a></div>
        <div class="col-md-1 row-title"><a id="notes">Notes</a></div>
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

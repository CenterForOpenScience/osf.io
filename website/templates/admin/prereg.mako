<%inherit file="base.mako"/>


<%def name="content()">
<div class="container" id="prereg-row">
    <div class="row">
        <H1 class="col-md-12">Pre-Registration Prize Admin View - Overview</H1>
    </div>
    <div class="row row-title">
        <div class="col-md-1 row-title"><a id="registration_metadata.q1.value" data-bind="click: setSort">Submission Title</a></div>
        <div class="col-md-1 row-title"><a id="initiator.fullname" data-bind="click: setSort">Name</a></div>
        <div class="col-md-1 row-title"><a id="initiator.username" data-bind="click: setSort">Email</a></div>
        <div class="col-md-1 row-title"><a id="initiated" data-bind="click: setSort">Begun</a></div>
        <div class="col-md-1 row-title"><a id="updated" data-bind="click: setSort">Submitted</a></div>
        <div class="col-md-1 row-title"><a id="comments_sent" data-bind="click: setSort">Comments Sent</a></div>
        <div class="col-md-1 row-title"><a id="new_comments" data-bind="click: setSort">New Comments</a></div>
        <div class="col-md-1 row-title"><a id="approved" data-bind="click: setSort">Approved</a></div>
        <div class="col-md-1 row-title"><a id="registered" data-bind="click: setSort">Registered</a></div>
        <div class="col-md-1 row-title"><a id="proof_of_pub" data-bind="click: setSort">Proof of Publication</a></div>
        <div class="col-md-1 row-title"><a id="payment_sent" data-bind="click: setSort">Payment Sent</a></div>
        <div class="col-md-1 row-title"><a id="notes" data-bind="click: setSort">Notes</a></div>
    </div>
    <div id="overview">
        <div class="row scripted">
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

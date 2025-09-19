<%inherit file="base.mako"/>
<%def name="title()">Pending Moderation</%def>
<%def name="description()">This ${resource_type} is pending moderation</%def>

<%def name="content()">
<style>
    /* Ensure content area has enough height so the footer sticks to the bottom */
    .pending-wrapper {
        min-height: calc(100vh - 180px); /* header+footer approximate height */
        display: -webkit-box;
        display: -ms-flexbox;
        display: flex;
        -webkit-box-align: center;
            -ms-flex-align: center;
                align-items: center;
    }
</style>

<div class="pending-wrapper">
    <div class="container">
        <div class='row'>
            <div class='col-md-12'>
                <div class="text-center">
                    <h2 id='pending-moderation-message'>Pending Moderation</h2>
                    <div class="alert alert-info">
                        <i class="fa fa-hourglass-half"></i>
                        <strong>This ${resource_type} is pending moderation at ${provider_name}</strong>
                        <p>This ${resource_type} has been submitted for review and is not yet publicly available.
                        Please check back later as moderation decisions may take some time.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
</%def>


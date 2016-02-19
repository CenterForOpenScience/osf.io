<%inherit file="base.mako"/>
<%def name="title()">Support</%def>

<%def name="stylesheets()">
    <link rel="stylesheet" href="/static/css/pages/support-page.css">
</%def>

<%def name="content()">
<div class="container">
    <h1> Support</h1>
    <div class="row m-t-md">
        <div class="col-md-8">
            <input type="text" class="form-control" placeholder="Search">
            <button class="btn btn-default">Clear Search</button>
            <button class="btn btn-default"> Expand All </button>
            <button class="btn btn-default"> Collapse All </button>

            <div class="row">
                <div class="col-sm-6">
                    <h3> Frequently Asked Questions </h3>

                </div>
                <div class="col-sm-6">
                    <h3> Getting Started with OSF </h3>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <h4 class="f-w-lg">Get in Touch</h4>
            <p> For emails about technical support:</p>
            <p> support@cos.io</p>
            <p> For all other questions or comments: </p>
            <p>contact@cos.io</p>
            <h4 class="f-w-lg"> Do you have Prereg Challenge related questions? </h4>
                <p>Check out our [Prereg section] on the cos.io website. </p>
            <h4 class="f-w-lg"> Are you looking for statistics consultations?</h4>
                <p>COS provides statistics consulation for free. To learn more about this service visit the [COS statistics consulting pages].</p>

            <h4 class="f-w-lg"> Other ways to get help </h4>
            <button class="btn btn-sm btn-default"> Ask us a question on twitter </button>
            <button class="btn btn-sm btn-default"> Join our mailing list </button>
            <button class="btn btn-sm btn-default"> Follow us on Facebook </button>

        </div>
    </div>
</div>
</%def>

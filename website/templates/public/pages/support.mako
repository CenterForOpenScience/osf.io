<%inherit file="base.mako"/>
<%def name="title()">Support</%def>

<%def name="stylesheets()">
    <link rel="stylesheet" href="/static/css/pages/support-page.css">
</%def>

<%def name="content_wrap()">
    <div class="watermarked">
            ${self.content()}
    </div><!-- end watermarked -->
</%def>



<%def name="content()">
<div class="support-wrapper">
    <div class="container">
        <h1 class="m-b-lg support-title"> Support</h1>

        <div class="row">
            <div class="col-sm-4">
                <div class="support-col">
                    ...
                </div>
            </div>
            <div class="col-sm-4">
                <div class="support-col">
                    ...
                </div>
            </div>
            <div class="col-sm-4">
                <div class="support-col">
                    <h4 class="f-w-lg">Get in Touch</h4>
                        <p> For emails about technical support:</p>
                        <p> <a href="mailto:support@cos.io" class="text-bigger">support@cos.io</a></p>
                        <p> For all other questions or comments: </p>
                        <p><a href="mailto:contact@cos.io" class="text-bigger">contact@cos.io</a></p>
                </div>
            </div>
        </div>


                        <h5 class="m-t-md f-w-xl"> Do you have Prereg Challenge related questions? </h5>
                            <p>Check out our <a href="https://cos.io/prereg/">Prereg section</a> on the cos.io website. </p>
                        <h5 class="m-t-md f-w-xl"> Are you looking for statistics consultations?</h5>
                            <p>COS provides statistics consulation for free. To learn more about this service visit the <a href="https://cos.io/stats_consulting/"> COS statistics consulting page</a>.</p>
                        <h5 class="m-t-md f-w-xl"> Other ways to get help </h5>
                        <button class="btn btn-sm btn-link"><i class="fa fa-twitter"></i> Ask us a question on twitter </button>
                        <button class="btn btn-sm btn-link"><i class="fa fa-users"></i> Join our mailing list </button>
                        <button class="btn btn-sm btn-link"><i class="fa fa-facebook"></i> Follow us on Facebook </button>
    </div>
</div>
</%def>

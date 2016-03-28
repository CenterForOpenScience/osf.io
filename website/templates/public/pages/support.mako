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
<div class="support-wrapper p-t-lg p-b-xl">
    <div class="container">
        <h1 class="m-b-lg support-title"> Support</h1>

        <div class="row m-b-lg">
            <div class="col-sm-4">
                <div class="support-col">
                    <div class="support-col-header bg-color-select">
                        <h4 class="f-w-lg"><a href="/faq"> Frequently Asked Questions</a></h4>
                    </div>
                    <div class="support-col-body clearfix">
                        <p> How can it be free? How will the OSF be useful to my research? What is a registration?
                        Get your questions about the Open Science Framework answered on our <a href="/faq"> FAQ page. </a></p>
                        <a href="/faq" class="btn btn-info m-t-lg pull-right" > Visit FAQ <i class="fa fa-angle-right"></i></a>
                    </div>

               </div>
            </div>
            <div class="col-sm-4">
                <div class="support-col">
                    <div class="support-col-header bg-color-select">
                        <h4 class="f-w-lg"><a href="/getting-started">Getting Started</a></h4>
                    </div>
                    <div class="support-col-body clearfix">
                        <p> Learn how to use the OSF for improving your research workflow. <a href="/getting-started">
                            Getting Started </a> has step-by-step video tutorials and screenshots that show you the basics
                            of project structures, version control, privacy, files, add-on support, and more! </p>
                            <a href="/getting-started" class="btn btn-info m-t-lg pull-right" > Visit Getting Started <i class="fa fa-angle-right"></i> </a>

                    </div>
                </div>
            </div>
            <div class="col-sm-4">
                <div class="support-col">
                    <div class="support-col-header bg-color-select">
                        <h4 class="f-w-lg">Get in Touch</h4>
                    </div>
                    <div class="support-col-body">
                        <p> For emails about technical support:</p>
                        <p> <a href="mailto:support@cos.io" class="text-bigger">support@cos.io</a></p>
                        <p> For all other questions or comments: </p>
                        <p><a href="mailto:contact@cos.io" class="text-bigger">contact@cos.io</a></p>
                    </div>
                </div>
            </div>
        </div>
        <hr>
        <div class="row m-b-lg">
            <div class="col-sm-6">
                <h5 class="m-t-md f-w-xl"> Do you have Prereg Challenge related questions? </h5>
                <p>Check out our <a href="https://cos.io/prereg/">Prereg section</a> on the cos.io website. </p>
            </div>
            <div class="col-sm-6">
                <h5 class="m-t-md f-w-xl"> Are you looking for statistics consultations?</h5>
                <p>COS provides statistics consulation for free. To learn more about this service visit the <a href="https://cos.io/stats_consulting/"> COS statistics consulting page</a>.</p>
            </div>

        </div>
        <hr>
        <div class="row m-b-lg">
            <div class="col-sm-12 text-center">
                <h4 class="m-t-md f-w-xl"> Other ways to get help </h4>
                <a href="https://twitter.com/OSFramework" class="btn btn-link"><i class="fa fa-twitter"></i> Ask us a question on twitter </a>
                <a href="https://groups.google.com/forum/#!forum/openscienceframework" class="btn btn-link"><i class="fa fa-users"></i> Join our mailing list </a>
                <a href="https://www.facebook.com/OpenScienceFramework" class="btn btn-link"><i class="fa fa-facebook"></i> Follow us on Facebook </a>
                <a href="https://github.com/centerforopenscience" class="btn btn-link"><i class="fa fa-github"></i> Connect with COS on Github</a>

            </div>
        </div>

    </div>
</div>
</%def>

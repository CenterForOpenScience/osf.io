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
                    <div class="text-center support-icon"><a href="/faq"><i class="fa fa-question"></i> </a></div>
                    <h4 class="f-w-lg"> Frequently Asked Questions</h4>
                    <p> How can it be free? How will the OSF be useful to my research? What is a registration?
                        Get your questions about the Open Science Framework answered on our <a href="/faq"> FAQ page. </a></p>
               </div>
            </div>
            <div class="col-sm-4">
                <div class="support-col">
                    <div class="text-center support-icon"><a href="/getting-started"><i class="fa fa-video-camera"></i></a></div>
                    <h4 class="f-w-lg">Getting Started</h4>
                    <p> Learn how to use the OSF for improving your research workflow. <a href="/getting-started">
                        Getting Started </a> has step-by-step video tutorials and screenshots that show you the basics
                        of project structures, version control, privacy, files, add-on support, and more! </p>
                </div>
            </div>
            <div class="col-sm-4">
                <div class="support-col">
                    <div class="text-center support-icon"><i class="fa fa-life-ring"></i></div>
                    <h4 class="f-w-lg">Get in Touch</h4>
                        <p> For emails about technical support:</p>
                        <p> <a href="mailto:support@cos.io" class="text-bigger">support@cos.io</a></p>
                        <p> For all other questions or comments: </p>
                        <p><a href="mailto:contact@cos.io" class="text-bigger">contact@cos.io</a></p>
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

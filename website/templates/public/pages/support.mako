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
                        Get your questions about the Open Science Framework answered on our <a href="http://help.osf.io/m/faqs/l/726460-faqs"> FAQ page. </a></p>
                        <a href="http://help.osf.io/m/faqs/l/726460-faqs" class="btn btn-info m-t-lg pull-right" > Visit FAQ <i class="fa fa-angle-right"></i></a>
                    </div>

               </div>
            </div>
            <div class="col-sm-4">
                <div class="support-col">
                    <div class="support-col-header bg-color-select">
                        <h4 class="f-w-lg"><a href="http://help.osf.io" target="_blank" rel="noreferrer">OSF Guides</a></h4>
                    </div>
                    <div class="support-col-body clearfix">
                        <p> Learn how to use the OSF for improving your research workflow. Read our <a href="http://help.osf.io" target="_blank" rel="noreferrer">
                            Guides </a> for step-by-step screenshots that show you the basics
                            of project structures, version control, privacy, files, add-on support, and more! </p>
                            <a href="http://help.osf.io" class="btn btn-info m-t-lg pull-right" target="_blank" rel="noreferrer"> Visit Guides <i class="fa fa-angle-right"></i> </a>

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
                        <p> <a href="mailto:${osf_support_email}" class="text-bigger">${osf_support_email}</a></p>
                        <p> For all other questions or comments: </p>
                        <p><a href="mailto:${osf_contact_email}" class="text-bigger">${osf_contact_email}</a></p>
                    </div>
                </div>
            </div>
        </div>
        <hr>

        <div class="row m-b-lg">
            <div class="col-sm-4">
                <h5 class="m-t-md f-w-xl"> Do you have Prereg Challenge related questions? </h5>
                <p>Check out our <a href="https://cos.io/prereg/">Prereg section</a> on the cos.io website. </p>
            </div>
            <div class="col-sm-4">
                <h5 class="m-t-md f-w-xl"> Are you experiencing downtime with our services? </h5>
                <p> Check out our<a href="https://status.cos.io"> status page</a> for updates on how our services are operating.</p>
            </div>
            <div class="col-sm-4">
                <h5 class="m-t-md f-w-xl"> Are you looking for statistics consultations?</h5>
                <p>COS provides statistics consulation for free. To learn more about this service visit the <a href="https://cos.io/stats_consulting/"> COS statistics consulting page</a>.</p>
            </div>

        </div>
        <hr>
        <div class="row m-b-lg">
            <div class="col-sm-12 text-center">
                <h4 class="m-t-md f-w-xl"> Other ways to get help </h4>
                <a href="https://twitter.com/OSFSupport" class="btn btn-link"><i class="fa fa-twitter"></i> Ask us a question on twitter </a>
                <a href="https://groups.google.com/forum/#!forum/openscienceframework" class="btn btn-link"><i class="fa fa-users"></i> Join our mailing list </a>
                <a href="https://www.facebook.com/CenterForOpenScience/" class="btn btn-link"><i class="fa fa-facebook"></i> Follow us on Facebook </a>
                <a href="https://github.com/centerforopenscience" class="btn btn-link"><i class="fa fa-github"></i> Connect with COS on GitHub</a>
            </div>
        </div>

    </div>
</div>
</%def>

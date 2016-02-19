<%inherit file="base.mako"/>
<%def name="title()">Support</%def>

<%def name="stylesheets()">
    <link rel="stylesheet" href="/static/css/pages/support-page.css">
</%def>

<%def name="content()">
<div class="container">
    <h1> Support</h1>
    <div class="row m-t-md">
        <div class="col-md-9">
            <input type="text" class="form-control support-filter" placeholder="Search">
            <button class="btn btn-default clear-search">Clear Search</button>
            <button class="btn btn-default expand-all"> Expand All </button>
            <button class="btn btn-default collapse-all"> Collapse All </button>

            <div class="row">
                <div class="col-md-6">
                    <h3> Frequently Asked Questions </h3>
                        <div class="support-item m-t-lg">
                            <h5 class="support-head f-w-xl"><i class="fa fa-angle-right"></i> How much does the OSF service cost?</h4>
                            <p class="support-body">It's free!</p>
                        </div>
                        <div class="support-item m-t-lg">
                            <h5 class="support-head f-w-xl"><i class="fa fa-angle-right"></i> How can it be free? How are you funded?</h4>
                            <p class="support-body">The OSF is maintained and developed by the <a href="http://cos.io">Center for Open Science</a> (COS), a non-profit organization. COS is supported through grants from a variety of supporters, including <a href="http://centerforopenscience.org/about_sponsors/"> federal agencies, private foundations, and commercial entities</a>.</p>
                        </div>
                        <div class="support-item m-t-lg">
                            <h5 class="support-head f-w-xl"><i class="fa fa-angle-right"></i> What if you run out of funding? What happens to my data?</h4>
                            <p class="support-body">Data stored on the OSF is backed by a $250,000 preservation fund that will provide for persistence of your data, even if the Center for Open Science runs out of funding. The code base for the OSF is entirely <a href="https://github.com/CenterForOpenScience/osf.io">open source</a>, which enables other groups to continue maintaining and expanding it if we aren’t able to.</p>
                        </div>
                        <div class="support-item m-t-lg">
                            <h5 class="support-head f-w-xl"><i class="fa fa-angle-right"></i> How will the OSF be useful to my research?</h4>
                            <p class="support-body">The OSF integrates with the scientist's daily workflow. The OSF helps document and archive study designs, materials, and data. The OSF facilitates sharing of materials and data within a laboratory or across laboratories. The OSF also facilitates transparency of laboratory research and provides a network design that details and credits individual contributions for all aspects of the research process. To see how it works, watch our short <a href="/getting-started">Getting Started</a> videos, see the <a href="https://osf.io/4znZP/wiki/home">OSF Features</a> page, or see how other scientists <a href="https://osf.io/svje2/">use the OSF.</a></p>
                        </div>
                        <div class="support-item m-t-lg">
                            <h5 class="support-head f-w-xl"><i class="fa fa-angle-right"></i> How can I help develop the OSF?</h4>
                            <p class="support-body">If you are a developer, check out the source code for the OSF <a href="https://github.com/CenterForOpenScience/osf.io">on GitHub</a>.
                            The <a href="https://github.com/CenterForOpenScience/osf.io/issues">issue tracker</a> is a good place to find ways to help. For more information, send an email to <a
                            href="mailto:contact@osf.io">contact@osf.io</a>.</p>
                        </div>
                        <div class="support-item m-t-lg">
                            <h5 class="support-head f-w-xl"><i class="fa fa-angle-right"></i> What is coming to the OSF?</h4>
                            <p class="support-body">For updates on new features, you can join our <a href="https://groups.google.com/forum/#!forum/openscienceframework">Google
                            Group</a>, find us on <a href="https://twitter.com/osframework">Twitter</a> and on <a href="https://www.facebook.com/OpenScienceFramework">Facebook</a>, or follow the COS <a href="https://github.com/centerforopenscience">GitHub</a> page.</p>
                        </div>
                        <div class="support-item m-t-lg">
                            <h5 class="support-head f-w-xl"><i class="fa fa-angle-right"></i> How can I contact the OSF team if I have a question that the FAQ or Getting Started pages don’t answer?</h4>
                            <p class="support-body">Send us an <a href="mailto:support@osf.io">email</a> and we'll be happy to help you.</p>
                        </div>


                </div>
                <div class="col-md-6">
                    <h3> Getting Started with OSF </h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <h4 class="f-w-xl">Get in Touch</h4>
            <p> For emails about technical support:</p>
            <p> support@cos.io</p>
            <p> For all other questions or comments: </p>
            <p>contact@cos.io</p>
            <h4 class="f-w-xl"> Do you have Prereg Challenge related questions? </h4>
                <p>Check out our [Prereg section] on the cos.io website. </p>
            <h4 class="f-w-xl"> Are you looking for statistics consultations?</h4>
                <p>COS provides statistics consulation for free. To learn more about this service visit the [COS statistics consulting pages].</p>

            <h4 class="f-w-xl"> Other ways to get help </h4>
            <button class="btn btn-sm btn-default"> Ask us a question on twitter </button>
            <button class="btn btn-sm btn-default"> Join our mailing list </button>
            <button class="btn btn-sm btn-default"> Follow us on Facebook </button>

        </div>
    </div>
</div>
<script src=${"/static/public/js/support-page.js" | webpack_asset}></script>

</%def>

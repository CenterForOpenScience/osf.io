<%inherit file="base.mako"/>
<%def name="title()">FAQ</%def>
<%def name="content()">

<style>
    h4 { margin-bottom: -5px }
</style>

<div class="nav-rows container">
    <div class="row">
        <div id="side-menu" class="col-sm-3 hidden-xs">
            <ul class="nav nav-pills nav-stacked m-t-xl affix" data-spy="affix">
                <li><a href="#about">About</a></li>
                <li><a href="#using">Using the OSF</a></li>
                <li><a href="#security">Privacy and Security</a></li>
                <li><a href="#common">Common Issues</a></li>
            </ul>
        </div>

        <div class="col-xs-12 col-sm-9">
            <div class="page-header">
                <h1>Frequently Asked Questions</h1>
            </div>

            <div id="about" class="anchor">
                <h3>About</h3>
                <div class="row m-l-lg">
                    <h4>How much does the OSF service cost?</h4>
                        <p class="p-b-sm">It's free!</p>

                    <h4>How can it be free? How are you funded?</h4>
                        <p class="p-b-sm">The OSF is maintained and developed by the <a href="http://cos.io">Center for Open Science</a> (COS), a non-profit organization. COS is supported through grants from a variety of supporters, including <a href="http://centerforopenscience.org/about_sponsors/"> federal agencies, private foundations, and commercial entities</a>.</p>

                    <h4>How will the OSF be useful to my research?</h4>
                        <p class="p-b-sm">The OSF integrates with the scientist's daily workflow. The OSF helps document and archive study designs, materials, and data. The OSF facilitates sharing of materials and data within a laboratory or across laboratories. The OSF also facilitates transparency of laboratory research and provides a network design that details and credits individual contributions for all aspects of the research process. To see how it works, watch our short <a href="/getting-started">Getting Started</a> videos, see the <a href="/4znZP/wiki/home">OSF Features</a> page, or see how other scientists <a href="/svje2/">use the OSF.</a></p>

                    <h4>How can I help develop the OSF?</h4>
                        <p class="p-b-sm">If you are a developer, check out the source code for the OSF <a href="https://github.com/CenterForOpenScience/osf.io">on GitHub</a>.
                        The <a href="https://github.com/CenterForOpenScience/osf.io/issues">issue tracker</a> is a good place to find ways to help. For more information, send an email to <a
                        href="mailto:contact@osf.io">contact@osf.io</a>.</p>


                    <h4>What is coming to the OSF?</h4>
                        <p class="p-b-sm">For updates on new features, you can join our <a href="https://groups.google.com/forum/#!forum/openscienceframework">Google
                        Group</a>, find us on <a href="https://twitter.com/osframework">Twitter</a> and on <a href="https://www.facebook.com/OpenScienceFramework">Facebook</a>, or follow the COS <a href="https://github.com/centerforopenscience">GitHub</a> page.</p>

                    <h4>How can I contact the OSF team if I have a question that the FAQ or Getting Started pages don’t answer?</h4>
                        <p class="p-b-sm">Send us an <a href="mailto:support@osf.io">email</a> and we'll be happy to help you.</p>

                </div>
            </div>
            <div id="using" class="anchor">
                <h3>Using the OSF</h3>
                <div class="row m-l-lg">
                    <h4>How can I get started on using the OSF?</h4>
                        <p class="p-b-sm">OSF membership is open and free, so you can
                            just register and check out our <a href="/getting-started">Getting Started</a>
                            page for a thorough run-down of how it works. This FAQ page will only cover a few of the most basic questions about the OSF, so it’s highly recommended that you read through Getting Started if you have any issues.</p>

                    <h4>How do I create a lab group/organizational group?</h4>
                        <p class="p-b-sm">The best way to create a lab or organizational group on the OSF is to create a project for that group. Then, individual projects within the lab can either be organized into components of the lab project or into their own projects which are linked to the lab group project. For an example, check out the <a href="https://osf.io/ezcuj/">Reproducibility Project: Psychology.</a></p>

                    <h4>What services can I use with the OSF?</h4>
                        <p class="p-b-sm">The OSF supports many third-party add-ons. For storage, you can connect to Amazon S3, Box, Dataverse, Dropbox, Figshare, Github, and Google Drive, and the OSF has its own default storage add-on, OSF Storage, if you choose not to connect to any third-party add-ons. The OSF also supports Mendeley and Zotero as citation managers. Please refer to the helpful <a href="/getting-started/#addons">Add-ons section</a> of our Getting Started page for more information on how to use add-ons.</p>

                    <h4>What can I do with a file after uploading it into a storage add-on?</h4>
                        <p class="p-b-sm">You can view, download, delete, and rename any files uploaded into OSF Storage. Files in third party storage add-ons might have restrictions on renaming and downloading.</p>

                    <h4>What is a registration?</h4>
                        <p class="p-b-sm">A registration is a frozen version of your project that can never be edited or deleted, but you can issue a retraction of it later, leaving behind basic metadata. When you create the registration, you have the option of either making it public immediately or making it private for up to four years through an embargo. A registration is useful for certifying what you did in a project in advance of data analysis, or for confirming the exact state of the project at important points of the lifecycle, such as manuscript submission or the onset of data collection.</p>

                    <h4>What if I don't want to register anything in the OSF?</h4>
                        <p class="p-b-sm">Registering is an optional feature of the OSF.</p>

                    <h4>What is the cap on data per user?</h4>
                        <p class="p-b-sm">There is a limit on the size of individual files uploaded to the OSF. This limit is 128 MB. If you have larger files to upload, you might consider utilizing add-ons. When archiving files during the registration process, there is a 1 GB total limit across all storage add-ons being archived.</p>

                    <h4>How do I get a DOI or ARK for my project?</h4>
                        <p class="p-b-sm">DOIs and ARKs are available for <b>public registrations</b> of projects. To get a DOI or ARK for your project, first create a registration of your project, and make sure the registration is public. Then click the "Create DOI / ARK" link, located in the block of text below the project title. A DOI and ARK will be automatically created. </p>

                </div>
            </div>

            <div id="security" class="anchor">
                <h3>Privacy and Security</h3>
                <div class="row m-l-lg">
                    <h4>What if I don't want to make anything available publicly in the OSF?</h4>
                        <p class="p-b-sm">
                            The OSF is designed to support both private and public workflows. You can
                            keep projects, or individual components of projects, private so that only
                            your project collaborators have access to them.</p>

                    <h4>How secure is my information?</h4>
                        <p class="p-b-sm">Security is extremely important for
                            the OSF. When you sign up and create a password, your password is not
                            recorded. Instead, we store a <a href="http://bcrypt.sourceforge.net/">bcrypt
                                hash</a> of your password. This is a computation on your password that
                            cannot be reversed, but is the same every time it is computed from your
                            password. This provides extra security. No one but you can know your
                            password. When you click "Forgot your password," the OSF sends you a new random
                            password because it neither stores nor has the ability to compute your password.
                            <br/><br/>
                            Data and materials posted on the OSF are not yet encrypted, unless you encrypt
                            them before uploading to the site. This means that if our servers were
                            compromised, the intruder would have access to raw data. While we have taken
                            technological measures to minimize this risk, the level of security can be
                            improved further. We will offer encryption soon, and we will partner with
                            data storage services that offer strong security features.</p>

                    <h4>Is the OSF HIPAA compliant?</h4>
                        <p class="p-b-sm">You should refer to your institutional policies regarding specific security requirements for your research.</p>

                    <h4>How can I license my data/code/etc.?</h4>
                        <p class="p-b-sm">If you’d like to attach a license to your materials hosted on the OSF, you can put this information in your project’s wiki or upload a README file. Typically, users wish to license their materials using Creative Commons licenses. Information about Creative Commons licenses can be found <a href="https://creativecommons.org/licenses/">here.</a> </p>


                    <h4>How does the OSF store and backup files that I upload to the site?</h4>
                        <p class="p-b-sm">The OSF stores files with <a href="http://www.rackspace.com/">Rackspace</a>
                            via an open source sponsorship, and has backups on
                            <a href="http://aws.amazon.com/glacier/">Amazon's Glacier platform</a>.
                            The OSF maintains several backup schemes, including off-site backups and
                            automated backups performed by our host every day, week, and fortnight.</p>
                </div>
            </div>

            <div id="common" class="anchor">
                <h3>Common Issues</h3>
                <div class="row m-l-lg">
                    <h4>What do I do if I lost my email confirmation for OSF registration, or I never received it?</h4>
                        <p class="p-b-sm">Log into the OSF with the email address and password of the account you created, and there will be a link to resend the confirmation email.</p>

                    <h4>My email address has changed. How do I change my login email?</h4>
                        <p class="p-b-sm">From your <a href="/settings/account">account settings</a> page, you can add additional email addresses to your account, and select which of these is your primary email address. Any of these emails can be used to log in to the OSF. </p>

                    <h4>I have multiple OSF accounts. How do I merge them into one account?</h4>
                        <p class="p-b-sm">Log into the account you wish to keep and navigate to your <a href="/settings/account/">account settings</a> page. There, enter the email address associated with your other OSF account. You will receive a confirmation link via email. Clicking the link will merge the projects and components into one account.</p>

                    <h4>How do I deactivate my OSF account?</h4>
                        <p class="p-b-sm">From your <a href="/settings/account/">account settings</a> page, you can request a deactivation of your OSF account. A member of the OSF admin must review your request and approve it. Once you deactivate your account, your account will no longer be associated with any OSF projects, and your work on the OSF will be inaccessible.</p>

                    <h4>What is the difference between a component and a folder?</h4>
                        <p class="p-b-sm">A folder can be used to organize files within a project or component - just like a folder on your own computer groups files together. A component is like a sub-project to help you organize different parts of your research. Components have their own privacy and sharing settings as well as their own unique, persistent identifiers for citation, and their own wiki and add-ons. You can also register a component on its own, without registering the parent project.</p>

                    <h4>How do I move a file from one storage add-on to another? Or one component to another?</h4>
                        <p class="p-b-sm">You can move files between components and add-ons, provided the components and add-ons are a part of the same project, by simply dragging and dropping from within the files widget of the project overview page or the Files tab. The Dataverse add-on does not currently support this feature.</p>

                    <h4>How do I rename a project?</h4>
                        <p class="p-b-sm">You can rename a project or a component by clicking on the project title in the project or component overview page.</p>

                    <h4>I’m using the search function in the top navigation bar to find one of my projects, but it’s not showing up in the results. What’s wrong?</h4>
                        <p class="p-b-sm">The search function only returns public projects, so if you’re searching for one of your own private projects, it won’t be returned in the results. To search for your own projects, go to your dashboard, and use the “Go to my project” widget on the top right.</p>

                    <h4>I have a DOI for my project on the OSF, but I've decided I'd rather host the material elsewhere. How can I do this without losing/needing a new DOI?</h4>
                        <p class="p-b-sm">Send us an email with your DOI and the new location of your materials and we'll update the URL associated with your DOI. </p>

                </div>
            </div>
        </div>
    </div>
</div>

</%def>

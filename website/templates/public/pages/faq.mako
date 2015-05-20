<%inherit file="base.mako"/>
<%def name="title()">FAQ</%def>
<%def name="content()">
<h1 class="page-title">Frequently Asked Questions</h1>
<h3>How much does the OSF service cost?</h3><p>It's free!</p>

<h3>How can it be free? How are you funded?</h3><p>OSF is
    maintained and developed by the Center for Open Science (COS), a non-profit
    organization. COS is supported through grants from a variety of supporters,
    including <a href="http://centerforopenscience.org/about_sponsors/">
    federal agencies, private foundations, and commercial entities</a>.</p>

<h3>How will the OSF be useful to my research?</h3><p>The OSF integrates with
    the scientist's daily workflow. OSF helps document and archive study
    designs, materials, and data. OSF facilitates sharing of materials and data
    within a laboratory or across laboratories. OSF also facilitates transparency of
    laboratory research and provides a network design that details and credits
    individual contributions for all aspects of the research process. To see how
    it works, watch our short <a
            href="/getting-started">Getting
        Started</a> videos, see the <a
            href="/4znZP/wiki/home">OSF
        Features </a>page, or see how other scientists <a href="/svje2/">use the OSF.</a></p>

<h3>How can I use the OSF?</h3><p>OSF membership is open and free, so you can
    just register and get started!</p>

<h3>What if I don't want to make anything available publicly in the OSF?</h3><p>
    The OSF is designed to support both private and public workflows. You can
    keep projects, or individual components of projects, private so that only
    your project collaborators have access to them.</p>

<h3>What is a registration?</h3><p>A registration certifies what was done in
    advance of data analysis or confirms the exact state of the project at
    important points of the lifecycle, such as manuscript submission or the
    onset of data collection.</p>

<h3>Do registrations have to be public?</h3><p>No. Registration can occur
    privately. Others could only know that a registration has occurred, but not
    what was registered. The most common use case of private registration is to
    keep a research design private before data collection is complete.</p>

<h3>What if I don't want to register anything in the OSF?</h3><p>Registering is
    an optional feature of the OSF.</p>

<h3>How secure is my information?</h3><p>Security is extremely important for
    the OSF. When you sign up and create a password, your password is not
    recorded. Instead, we store a <a href="http://bcrypt.sourceforge.net/">bcrypt
        hash</a> of your password. This is a computation on your password that
    cannot be reversed, but is the same every time it is computed from your
    password. This provides extra security. No one but you can know your
    password. When you click "Forgot your password," OSF sends you a new random
    password because it neither stores nor has the ability to compute your password.</p>

<p>Data and materials posted on OSF are not yet encrypted, unless you encrypt
    them before uploading to the site. This means that if our servers were
    compromised, the intruder would have access to raw data. While we have taken
    technological measures to minimize this risk, the level of security can be
    improved further. We will offer encryption soon, and we will partner with
    data storage services that offer strong security features.</p>

<h3>How does OSF store and back up files that I upload to the site?</h3>
    <p>The OSF stores files with <a href="http://www.rackspace.com/">Rackspace</a>
    via an open source sponsorship, and has backups on
    <a href="http://aws.amazon.com/glacier/">Amazon's Glacier platform</a>.
    OSF maintains several backup schemes, including off-site backups and
    automated backups performed by our host every day, week, and fortnight.</p>

<h3>What is coming to the OSF?</h3>

<p>The OSF infrastructure will be open-sourced to encourage a community of
    developers to contribute to open science by adding features and improving
    existing features. For updates on new features, you can join our <a href="https://groups.google.com/forum/#!forum/openscienceframework">Google
        Group</a>, find us on <a
            href="https://twitter.com/osframework">Twitter</a> and on <a
            href="https://www.facebook.com/OpenScienceFramework">Facebook</a>,
    or follow the COS <a
            href="https://github.com/centerforopenscience">GitHub</a> page.</p>
<h3>How can I help develop the OSF?</h3><p>If you are a developer, email the <a
        href="mailto:contact@osf.io">dev team</a> for
    more information. If you want to comment on how to make the OSF more useful
    for managing your workflow, send comments <a
            href="mailto:contact@osf.io">here</a>.</p>

<h3>Is the OSF HIPAA compliant?</h3>
<p>You should refer to your institutional policies regarding specific security requirements for your research.</p>

<h3>What is the cap on data per user?</h3>
<p>There is a limit on the size of individual files uploaded to the OSF. This limit is 128 mb. If you have larger files to upload, you might consider utilizing add-ons.</p>

<h3>How do I get a DOI or ARK for my project?</h3>
<p>DOIs and ARKs are available for <b>public registrations</b> of projects. To get a DOI or ARK for your project, first create a registration of your project, and make sure the registration is public. Then click "Create DOI / ARK" link, located in the block of text below the project title. A DOI and ARK will be automatically created. </p>

<h3>I have a DOI for my project on the OSF, but I've decided I'd rather host the material elsewhere. How can I do this without losing/needing a new DOI?</h3>
<p>Send us an email with your DOI and the new location of your materials and we'll update the URL associated with your DOI. </p>

<h3>How do I rename a project?</h3>
<p>You can rename a project or a component by clicking on the project title in the project or component overview page.</p>

<h3>Can I move a component to another project? Or a file to a different component?</h3>
<p>At this time, it is not possible to move a component to another project, nor is it possible to move a file between components. You will have to delete the component or file and re-upload it to the appropriate location. There are plans to implement these features in the future.</p>

<h3>Can I rename files after they are uploaded?</h3>
<p>Unfortunately, no - you will have to delete the file and re-upload a new file with the desired name.</p>

<h3>My email address has changed. How do I change my login email?</h3>
<p>From your <a href="https://osf.io/settings/account">account settings</a> page, you can additional email addresses to your account, and select which of these is your primary email address. Any of these emails can be used to log in to the OSF. </p>

<h3>How can I license my data/code/etc.?</h3>
<p>If you’d like to attach a license to your materials hosted on the OSF, you can put this information in your project’s wiki or upload a README file. Typically, users wish to license their materials using Creative Commons licenses. Information about Creative Commons licenses can be found <a href="https://creativecommons.org/licenses/">here.</a> </p>

<h3>How do I create a lab group/organizational group?</h3>
<p>The best way to create a lab or organizational group on the OSF is to create a project for that group. Then, individual projects within the lab can either be organized into components of the lab project or into their own projects which are linked to the lab group project. For an example, check out the <a href="https://osf.io/ezcuj/">Reproducibility Project: Psychology.</a></p>

<h3>I have multiple OSF accounts. Can I merge them into one account?</h3>
<p>Yes. Log into the account you wish to keep and navigate to your Account Settings. There, enter the email address associated with your other OSF account. You will receive a confirmation link via email. Clicking the link will merge the projects and components under one account.</p>

<h3>What is the difference between a component and a folder?</h3>
<p>A folder can be used to organize files within a project or component - just like a folder on your own computer groups files together. A component is like a sub-project to help you organize different parts of your research. Components have their own privacy and sharing settings as well as their own unique, persistent identifiers for citation, and their own wiki and add-ons.</p>

<h3>I’m using the search function to find one of my projects, but it’s not showing up in the results. What’s wrong?</h3>
<p>The search function only returns public projects, so if you’re searching for one of your own private projects, it won’t be returned in the results. To search for your own projects, go to your dashboard, and use the “Go to my project” widget on the top right.</p>

<h3>None of these FAQs answered my question. Now what?</h3>
<p>Send us an <a href="mailto:support@osf.io">email</a> and we'll be happy to answer your questions.


</%def>

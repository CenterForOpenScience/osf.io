## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
        <br>
        Dear ${fullname},
        <br><br>
        You have an unsubmitted preregistration on the Open Science Framework that could be eligible for a $1,000 prize as part of the Prereg Challenge. If you would like this to be considered for a prize, please complete <a href="${prereg_url}">your preregistration</a> from your project ${project_name} and submit it for review, available on the last page of the preregistration form. This review process is required for a prize and simply checks to make sure the preregistration includes a complete analysis plan.
        If you have questions about a particular field in the preregistration, you may review the <a href="https://cos.io/prereg">FAQ on the website</a>, <a href="mailto:prereg@cos.io">email us with a question</a>, or use our <a href="https://cos.io/stats_consulting">free statistical consulting services</a>.
        Thank you for using the OSF!
        <br><br>
        Sincerely,
        <br>
        The team at the Center for Open Science
    </div>
</%def>

## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
        <br>
        Hello ${fullname},
        <br><br>
        Thanks for adding your presentation from ${conference} to the conference’s <a href="${osf_url}">Open Science Framework</a> (OSF) page! Sharing virtually is an easy way to increase the impact of your research.
        <br>
        %if downloads > 4:
        Your project files have been downloaded ${downloads} times!
        %endif
        <br>
        Have you considered adding your manuscript, data, or other research materials to the project? Adding these materials means:
        <ul>
            <li>When someone finds your poster or talk, they can see and cite the accompanying data</li>
            <li>You have one place to reference when looking for your research materials</li>
            <li>You can monitor interest in your data and materials by tracking downloads, just like you can for your ${conference} presentation.</li>
        </ul>
        To learn more about how the OSF can help you manage your research, begin with these (short!) videos on our <a href="${osf_url}getting-started">Getting Started</a> page. Or, read about how others use the OSF from a <a href="https://osf.io/7a8gs/">case study</a>.
        The best part? It’s all free! OSF is supported by the non-profit technology company, the <a href="http://cos.io/">Center for Open Science</a>.
        <br><br>
        Best wishes,
        <br>
        COS Support Team
        <br><br>
        P.S. Got questions? <a href="mailto:support@osf.io">Just send us an email!</a>
    </div>
</%def>
<%def name="footer()">
    <br>
    The <a href="${osf_url}">Open Science Framework</a> is provided as a free, open source service from the <a href="http://cos.io/">Center for Open Science</a>.
</%def>

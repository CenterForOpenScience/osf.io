## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
        <br>
        Hello ${fullname},
        <br><br>
        Thanks for adding your presentation from ${conference} to the conference's <a href="${osf_url}">GakuNin RDM</a> (GRDM) page! Sharing virtually is an easy way to increase the impact of your research.
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
        To learn more about how the GakuNin RDM can help you manage your research, read our <a href="http://help.osf.io">Guides</a>. Or, read about how others use the GakuNin RDM from a <a href="https://osf.io/svje2/">case study</a>.
        The best part? It’s all free! GakuNin RDM is supported by the non-profit technology company, the <a href="https://nii.ac.jp/">National Institute of Informatics</a>.
        <br><br>
        Best wishes,
        <br>
        NII Support Team

        <br><br>
        P.S. Got questions? <a href="mailto:${osf_support_email}">Just send us an email!</a>
    </div>
</%def>
<%def name="footer()">
    <br>
    The <a href="${osf_url}">GakuNin RDM</a> is provided as a free, open source service from the <a href="https://nii.ac.jp/">National Institute of Informatics</a>.
</%def>

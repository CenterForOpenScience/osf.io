<%inherit file="base.mako"/>
<%def name="title()">About</%def>
<%def name="content()">
<div class="page-header">
    <h1>About Open Science Framework</h1>
</div>
<p>
    Open Science Framework (OSF) in conjunction with the broader Open Science Collaboration (OSC) is an open collaboration of scientists to increase the alignment between scientific values and scientific practices (<a href="/howosfworks">How the OSF works</a>).  Efforts include development of tools and infrastructure, and conducting research about scientific practices.
</p>
<p>
Some tools and infrastructure projects:
<ul>
    <li>Open Science Framework: Document, archive, share, and find study materials in a web-based project management system for scientists [Coordinators: <a href="http://people.virginia.edu/~js6ew">Jeffrey Spies</a> and <a href="http://briannosek.com">Brian Nosek</a>]
        <li>Replication Value: Developing a statistic to identify published effects that are important to replicate. [Coordinator: Daniel Lakens]
</ul>
</p>
<p>
Some research projects
<ul>
<li><a href="/reproducibility">Reproducibility Project</a>: A large-scale collaboration to estimate the reproducibility of published psychological science. [Coordinator: <a href="http://briannosek.com">Brian Nosek</a>]
<li>Opinions about Disclosure Standards: A survey assessing psychological scientists opinions about disclosure standards recommended by Simmons, Nelson, and Simonsohn (2011). [Coordinators: Heather Fuchs and Susann Fiedler]
</ul>
</p>
<p>
Read more about current projects, <a href="/howosfworks">how the OSF works</a>, or join the <a href="http://groups.google.com/group/openscienceframework/">OSF discussion group</a>.
</p>

<h3>The promise of open science collaboration</h3>
<p>
Done well, open science collaboration can radically transform scientific practice.
Scientific expertise is distributed across many minds,
but scientific problems are rarely localized to the existing expertise of one or a few minds.
Broadcasting problems openly increases the odds a person with the right expertise will see it and be able to solve it easily.
This means that solutions can be identified quickly rather than requiring lots of additional self-training by the idea originator
(who may not even know what training to get).
Likewise, with many people drawing on distinct expertise,
novel solutions may emerge rapidly that would not have been identified by individuals or small groups.
In addition to better and faster problem-solving,
open projects can be more ambitious because more areas of expertise (and hands) can contribute to a problem without as much time or resource investment by any individual.
For example, it is much easier to contribute on issues that are central to one's skills/expertise than to build new expertise.
Simultaneously knowledge gain for each contributor can be rapid because they learn from each other's contributions on a shared problem.
Finally, there are many ways to contribute productively on large-scale projects--data coding, collection, analysis, writing, conceptualization, design, coordination, etc.
In such projects, all contributions are essential and valued meaning that many areas and levels of expertise can contribute productively together--from senior renowned expert to citizen scientist.
</p>
<h3>How open science collaboration can work</h3>
<p>
There are multiple threats that will kill an open science group--particularly in managing the collective effort with the constraints of individual contributions.
Michael Nielsen summarizes these very well in Reinventing Discovery.
A successful open science collaboration must: (a) modularize: split up the tasks into independent components, (b) encourage small contributions, (c) develop a well-structured information commons, and (d) maintain individual incentives to participate
These lower the barriers to entry for new contributors, and maximize the range of expertise input potential.
Individuals should see that getting involved in a project can be done easily, even if the project is underway.
Ideally, it should be possible to make meaningful contributions with whatever time and interest is available.
The Open Science Framework (OSF) involves continuously refining these practices as much as actually executing the projects themselves.
See <a href="/howosfworks">how the OSF works</a> for more detail.
</p>
<h3>OSF Features</h3>
<p>
The OSF web application is part network of research materials, part version control system, and part collaboration software.
</p>

<dl>
<dt>Document and archive studies</dt>
<dd>Move the organization and management of study materials from the desktop into the cloud.  Labs can organize, share, and archive study materials among team members.  Web-based project management reduces the likelihood of losing study materials due to computer malfunction, changing personnel, or just forgetting where you put the damn thing.</dd>

<dt>Share and find materials</dt>
<dd>With a click, make study materials public so that other researchers can find, use and cite them.  Find materials by other researchers to avoid reinventing something that already exists.</dd>


<dt>Detail individual contribution</dt>
<dd>Assign citable, contributor credit to any research material - tools, analysis scripts, methods, measures, data.</dd>

<dt>Increase transparency</dt>
<dd>Make as much of the scientific workflow public as desired - as it is developed or after publication of reports.</dd>

<dt>Time-stamp materials</dt>
<dd>When a strong a priori hypothesis exists, registering materials certifies what was done in advance of data collection or analysis.  When many labs are working on similar questions, registration affirms the date and time of designs, data collections, and discoveries.</dd>
</dl>
<p>
Interested in using the system? <a href="mailto:betainvite@openscienceframework.org">Request an invitation</a> to try out the upcoming beta-release.
</p>
<p>
Interested in being a developer?  Contact <a href="mailto:jspies@virginia.edu.edu">Jeff Spies</a> about development plans and open-sourcing of the project.
</p>
<p>
Have ideas to make the OSF useful to you?  <a href="mailto:feedback@openscienceframework.org">Submit them here</a>.
</p>
</%def>

<%def name="footer()">
    <%include file="footer.mako" args="placement=''"/>
</%def>

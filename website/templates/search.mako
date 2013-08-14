<%inherit file="contentContainer.mako" />
<%namespace file="_node_list.mako" import="node_list"/>
<%
    import framework
%>
<section id="Search">
    <div class="page-header">
        <h1>Search <small>${total} result${'s' if total is not 1 else ''} in ${time} seconds</small></h1>
    </div>
</section>
<div class="row">
    <div class="span2">
        <h3>Everything</h3>
        <h3>Projects</h3>
        <h3>Nodes</h3>
        <h3>Files</h3>        
    </div>
    <div class="span10">
        % if results:
            ${node_list(results)}
        % else:
            No results found. <br />
            <br />
            Note: Improvements are currently being made on the search engine, so it might have been reasonable to find something based upon your search terms. Feel free to <a href="mailto:jspies@virginia.edu">send me</a> the terms you used and what you expected to find, and I'll use that information to potentially tune the search algorithm. Thanks!
        %endif
    </div>
</div>
<%inherit file="base.mako"/>
<%def name="title()">${node['ownerName']} Files</%def>

<%def name="content()">

    <h1 class="text-center">Hello ${node['ownerName']}, this is where we put the code.</h1>

</%def>


<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}

</%def>

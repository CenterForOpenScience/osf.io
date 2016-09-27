<%inherit file="base.mako"/>
<%def name="title()">SHARE Help</%def>
<%def name="content()">
    <div class="embed-responsive embed-responsive-4by3" style="margin-top: 20px;">
    <iframe class="embed-responsive-item" src="${help}"></iframe>
    </div>
</%def>

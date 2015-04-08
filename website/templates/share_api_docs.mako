<%inherit file="base.mako"/>
<%def name="title()">SHARE Help</%def>
<%def name="content()">
    <div class="embed-responsive embed-responsive-4by3">
    <iframe class="embed-responsive-item" src="${help | js_str}"></iframe>
    </div>
</%def>

<%inherit file="base.mako"/>

<%def name="content()">
    <ul>
    %for post in posts:
        <li>${post.get('name')}</li>
    %endfor
    </ul>
</%def>

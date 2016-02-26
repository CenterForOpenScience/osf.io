<%def name="logged_in(name)">
    %if name != '':
        <%include file="home.mako"/>
    %else:
        <%include file="landing.mako"/>
    %endif
</%def>

${logged_in(user_name)}

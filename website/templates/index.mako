<%def name="logged_in(name)">

    %if name != '':
        <%include file="home.mako"/>
    %else:
        %if home:
            <%include file="landing.mako"/>
        %else:
            <%include file="institution.mako"/>
        %endif
    %endif
</%def>

${logged_in(user_name)}


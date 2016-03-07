<%def name="logged_in(name)">
    %if name != '':
        %if home:
            <%include file="home.mako"/>
        %else:
            <%include file="institution.mako"/>
        %endif
    %else:
        %if home:
            <%include file="landing.mako"/>
        %else:
            <%include file="institution.mako"/>
        %endif
    %endif
</%def>

${logged_in(user_name)}


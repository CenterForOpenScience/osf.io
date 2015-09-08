${ spa(spa_config) }

<%def name="spa(data)">
<%
tmpl = data['template_lookup'].get_template(data['root_template']).render(**data)
%>   
${tmpl | n}
</%def>

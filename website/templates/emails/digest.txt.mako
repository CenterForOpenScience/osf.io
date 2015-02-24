<% from website.models import Node %>
<%
def print_message(d, indent=0):
    message = ''
    for key in d['children']:
        message += '\t' * indent + ' - ' + Node.load(key).title + ':'
        if d['children'][key]['messages']:
            for m in d['children'][key]['messages']:
                message += '\n' +'\t' * (indent+1) + ' - '+ m

        if isinstance(d['children'][key]['children'], dict):
            message += '\n' + print_message(d['children'][key], indent+1)

    return message
%>

Hello ${name},

Summary:
${build_message(message)}
From the Open Science Framework

<%def name="build_message(d, indent=0)">
%for key in d['children']:
    ${'\t' * indent + Node.load(key).title + ':'}
    %if d['children'][key]['messages']:
        %for m in d['children'][key]['messages']:
        ${'\t' * indent + '- ' + m['message'] + ' ' + m['timestamp'].strftime("%H:%M")}
        %endfor
    %endif
    %if isinstance(d['children'][key]['children'], dict):
        ${build_message(d['children'][key], indent+1)}
    %endif
%endfor
</%def>
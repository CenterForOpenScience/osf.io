Hello ${user.fullname},

% if is_initiator:
You initiated a request to end the embargo for a registration of ${project_name}${context.get('custom_message', '')}. The embargoed registration can be viewed here: ${registration_link}.
% else:
${initiated_by} initiated a request to end the embargo for a registration of ${project_name}${context.get('custom_message', '')}. The embargoed registration can be viewed here: ${registration_link}.
% endif

To approve this change and to make this registration public immediately, click the following link: ${approval_link}.

To cancel this change, click the following link: ${disapproval_link}.

Sincerely yours,

The GakuNin RDM Robots

National Institute of Informatics

2-1-2 Hitotsubashi, Chiyoda Ward, Tokyo 101-8430, JAPAN

Privacy Policy: https://meatwiki.nii.ac.jp/confluence/pages/viewpage.action?pageId=32676422

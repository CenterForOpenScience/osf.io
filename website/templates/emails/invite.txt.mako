<%doc>
    Purpose:
    This message is an invitation to an unregistered user to join a project or component.

    Sent When:
    The the project admin invites an unregistered contribution by adding them and giving there email.

    Agents:
    invitedUser: User, invited to project and must claim token.
    referrer: User, invited invitedUser user to join thier project/component.
    node: Node, the node refferer invited invitedUser to.
</%doc>
<%!
    from website import settings
%>
Hello ${invitedUser.fullname},


You have been added by ${referrer.fullname} as a contributor to the project "${node.title}" on the Open Science Framework. To set a password for your account, visit:

${claim_url}

To preview ${node.title} click the following link: ${node.absolute_url}

(NOTE: if this project is private, you will not be able to view it until you have confirmed your account)

Once you have set a password, you will be able to make contributions to ${node.title} and create your own projects. You will automatically be subscribed to notification emails for this project. To change your email notification preferences, visit your project or your user settings: ${settings.DOMAIN + "settings/notifications/"}

If you are not ${invitedUser.fullname} or you are erroneously being associated with ${node.title} then email contact@osf.io with the subject line "Claiming Error" to report the problem.

Sincerely,

Open Science Framework Robot



Want more information? Visit https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science. Questions? Email contact@osf.io


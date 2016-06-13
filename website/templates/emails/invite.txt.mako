<%doc>
    Purpose:
        This message is sent when an admin invites an unregistered User to a project or component

        invitedUser: User, invited to project and must claim token.
        referrer: User, invited invitedUser user to join thier project/component.
        node: Node, the node refferer invited invitedUser to.
</%doc>

Hello ${invitedUser.fullname},

You have been added by ${referrer.fullname} as a contributor to the project "${node.title}" on the Open Science Framework. To set a password for your account, visit:

${claim_url}

To preview ${node.title} click the following link: ${node.absolute_url}

(NOTE: if this project is private, you will not be able to view it until you have confirmed your account)

If you are not ${invitedUser.fullname} or you are erroneously being associated with ${node.title} then email contact@osf.io with the subject line "Claiming Error" to report the problem.

Sincerely,

Open Science Framework Robot



Want more information? Visit https://osf.io/ to learn about the Open Science Framework, or https://cos.io/ for information about its supporting organization, the Center for Open Science. Questions? Email contact@osf.io


## -*- coding: utf-8 -*-
<div style="margin: 40px;">
    <p>Hello ${recipient.fullname},</p>
        <p>
            The ${reviewable.provider.preprint_word}
            <a href="${reviewable.absolute_url}">${reviewable.node.title}</a>
            has been successfully re-submitted to ${reviewable.provider.name}.
        </p>
        <p>
            ${reviewable.provider.name} has chosen to moderate their submissions using a
            pre-moderation workflow, which means your submission is pending until accepted
            by a moderator.
            % if not no_future_emails:
                You will receive a separate notification informing you of any status changes.
            % endif
        </p>
        <p>
            You will ${'not receive ' if no_future_emails else 'be automatically subscribed to '}future
            notification emails for this ${reviewable.provider.preprint_word}. Each
            ${reviewable.provider.preprint_word} is associated with a project on the Open Science
            Framework for managing the ${reviewable.provider.preprint_word}. To change your email
            notification preferences, visit your
            <a href="${domain + 'settings/notifications/'}">user settings</a>.
        </p>
        <p>
            If you have been erroneously associated with "${reviewable.node.title}", then you
            may visit the project's "Contributors" page and remove yourself as a contributor.
        </p>
        <p>
            For more information about ${reviewable.provider.name}, visit
            <a href="${provider_url}">${provider_url}</a> to learn more. To learn about the
            GakuNin RDM, visit <a href="https://rdm.nii.ac.jp/">https://rdm.nii.ac.jp/</a>.
        </p>
        <p>For questions regarding submission criteria, please email ${provider_contact_email}</p>
        <br>
        Sincerely,<br>
        Your ${reviewable.provider.name} and GakuNin RDM teams
        <p>
            National Institute of Informatics<br>
            210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903
        </p>
        <a href="https://meatwiki.nii.ac.jp/confluence/pages/viewpage.action?pageId=32676422">Privacy Policy</a>
</div>


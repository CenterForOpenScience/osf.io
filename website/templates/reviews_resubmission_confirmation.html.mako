<%inherit file="notify_base.mako" />
<%def name="content()">
    <div style="margin: 40px;">
       <p>
            Hello ${referrer_fullname},
       </p>
       <p>
            The ${document_type} <a href="${reviewable_absolute_url}">${reviewable_title}</a> has been successfully
            resubmitted to ${reviewable_provider_name}.
       </p>
       <p>
            ${reviewable_provider_name} has chosen to moderate their submissions using a pre-moderation workflow, which
            means your submission is pending until accepted by a moderator.
            % if not no_future_emails:
                You will receive a separate notification informing you of any status changes.
            % endif
       </p>
       <p>
            You will ${'not receive ' if no_future_emails else 'be automatically subscribed to '}future notification emails
            for this ${document_type}.
       </p>
       <p>
           If you have been erroneously associated with "${reviewable_title}", then you may visit the ${document_type}'s
           "Edit" page and remove yourself as a contributor.
       </p>
       <p>
            For more information about ${reviewable_provider_name}, visit <a href="${provider_url}">${provider_url}</a> to
            learn more. To learn about the Open Science Framework, visit <a href=" "> </a>.
       </p>
       <p>
            For questions regarding submission criteria, please email ${provider_contact_email}
       </p>
       <br>
       Sincerely,
       <br>
       Your ${reviewable_provider_name} and OSF teams
       <p>
            Center for Open Science<br> 210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903
       </p>
       <a href="https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>
    </div>
</%def>

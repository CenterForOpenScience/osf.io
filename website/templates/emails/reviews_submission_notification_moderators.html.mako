## -*- coding: utf-8 -*-
<%!
    from website import settings
%>
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">

        <p>
            Hello ${user.fullname},
        </p>

        <p>
            A new ${reviewable.provider.preprint_word} has been submitted to ${reviewable.provider.name},
            powered by OSF: <a href=${reviewable.absolute_url}> ${reviewable.node.title}</a> submitted by
            ${', '.join(reviewable.node.contributors.values_list('fullname', flat=True))}.
        </p>

        <p>
            To accept or reject this submission, click the link above or visit your
            <a href=${settings.DOMAIN + 'reviews/preprints/{}/{}'.format(reviewable.provider._id, reviewable._id)}>provider’s submissions</a>.
        </p>

        <p>
            You are receiving these emails because you are ${'an administrator' if is_admin else 'a moderator'}
            on ${reviewable.provider.name}.
            To change your email notification preferences,
            visit your <a href=${settings.DOMAIN + '/reviews/notifications'}>notification settings</a>.
        </p>

        <p>
            Sincerely,<br>
            Your ${reviewable.provider.name} and OSF teams
        </p>

        <p>
            Center for Open Science<br>
            210 Ridge McIntire Road, Suite 500, Charlottesville, VA 22903
        </p>

        <a href="https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>
    </div>
</%def>

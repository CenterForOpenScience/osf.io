<h2 style="padding-bottom: 30px;">
  ${ meeting['name'] }
</h2>

% if meeting['location']:
   <span>${meeting['location']}</span>
% endif
% if meeting['location'] and meeting['start_date']:
    |
% endif
% if meeting['start_date']:
    <span>${meeting['start_date'].strftime('%b %d, %Y')}</span>
    %if meeting['end_date']:
        - <span>${meeting['end_date'].strftime('%b %d, %Y')}</span>
    %endif
% endif

% if meeting['logo_url']:
    <img src="${ meeting['logo_url'] }" class="img-responsive" />
    <br /><br />
  % endif

% if meeting['active']:
    <div>
        <a id="addLink" onclick="" href="#">${('Add your ' + meeting['field_names']['add_submission']) if meeting['poster'] and meeting['talk'] else ('Add your ' + meeting['field_names']['submission1_plural']) if meeting['poster'] else ('Add your ' + meeting['field_names']['submission2_plural'])}</a>

        % if meeting['info_url']:
          | <a href="${ meeting['info_url'] }">${meeting['field_names'].get('homepage_link_text', 'Conference homepage')}</a>
        % endif
    </div>

    <div style="display: none" id="submit">
        <h3>${('Add your ' + meeting['field_names']['add_submission']) if meeting['poster'] and meeting['talk'] else ('Add your ' + meeting['field_names']['submission1_plural']) if meeting['poster'] else ('Add your ' + meeting['field_names']['submission2_plural'])}</h3>
        <p>
            Send an email to the following address(es) from the email
            account you would like used on the GakuNin RDM:
        </p>
        <ul>
            % if meeting['poster']:
                <li>For ${meeting['field_names']['submission1_plural']}, email <a href="mailto:${ label }-${meeting['field_names']['submission1']}@osf.io">${ label }-${meeting['field_names']['submission1']}@osf.io</a></li>
            % endif
            % if meeting['talk']:
                <li>For ${meeting['field_names']['submission2_plural']}, email <a href="mailto:${ label }-${meeting['field_names']['submission2']}@osf.io">${ label }-${meeting['field_names']['submission2']}@osf.io</a></li>
            % endif
        </ul>
        <p>The format of the email should be as follows:</p>
        <div>
            <dl style="padding-left: 25px">
                <dt>Subject</dt>
                <dd>${meeting['field_names']['mail_subject']}</dd>
                <dt>Message body</dt>
                <dd>${meeting['field_names']['mail_message_body']}</dd>
                <dt>Attachment</dt>
                <dd>${meeting['field_names']['mail_attachment']}</dd>
            </dl>
        </div>
        <p>
            Once sent, we will follow-up by sending you the permanent identifier
            that others can use to cite your work; you can also login and make changes,
            such as uploading additional files, to your project at that URL. If you
            didn't have an GakuNin RDM account, one will be created automatically and a link
            to set your password will be emailed to you; if you do, we will simply create
            a new project in your account. By creating an account you agree to our
            <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/TERMS_OF_USE.md">Terms</a>
            and that you have read our
            <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>,
            including our information on
            <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md#f-cookies">Cookie Use</a>.
        </p>
    </div>
% endif

<div id="grid" style="width: 100%;"></div>

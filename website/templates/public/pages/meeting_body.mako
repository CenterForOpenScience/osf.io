<h2 style="padding-bottom: 30px;">${ meeting['name'] }
    ${meeting['field_names']['meeting_title_type'] if meeting['poster'] and meeting['talk'] else 'Posters' if meeting['poster'] else 'Talks'}
</h2>

% if meeting['logo_url']:
    <img src="${ meeting['logo_url'] }" class="img-responsive" />
    <br /><br />
  % endif

% if meeting['active']:
    <div>
        <a id="addLink" onclick="" href="#">${('Add your ' + meeting['field_names']['add_submission']) if meeting['poster'] and meeting['talk'] else ('Add your ' + meeting['field_names']['submission1_plural']) if meeting['poster'] else ('Add your ' + meeting['field_names']['submission2_plural'])}</a>

        % if meeting['info_url']:
          | <a href="${ meeting['info_url'] }" target="_blank">Conference homepage <i class="fa fa-sm fa fa-external-link"></i></a>
        % endif
    </div>

    <div style="display: none" id="submit">
        <h3>${('Add your ' + meeting['field_names']['add_submission']) if meeting['poster'] and meeting['talk'] else ('Add your ' + meeting['field_names']['submission1_plural']) if meeting['poster'] else ('Add your ' + meeting['field_names']['submission2_plural'])}</h3>
        <p>
            Send an email to the following address(es) from the email
            account you would like used on the OSF:
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
            didn't have an OSF account, one will be created automatically and a link
            to set your password will be emailed to you; if you do, we will simply create
            a new project in your account.
        </p>
    </div>
% endif

<div id="grid" style="width: 100%;"></div>

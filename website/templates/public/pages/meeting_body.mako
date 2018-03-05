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
            a new project in your account. By creating an account you agree to our
            <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/TERMS_OF_USE.md">Terms</a>
            and that you have read our
            <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>,
            including our information on
            <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md#f-cookies">Cookie Use</a>.
        </p>
    </div>
% endif

<div class="tb-head">
    <div class="tb-head-filter col-xs-12 col-sm-6 col-sm-offset-6">
        <form id="meetingsFilter" method="GET">
            <input type="hidden" name="page" value="1">
            <input id="filterAttachments" placeholder="Search" value="${ q }" name="q" type="text" style="width:100%;display:inline;" class="pull-right form-control">
            <input type="hidden" name="sort" value="${ sort }">
        </form>
    </div>
</div>

<div style="width: 100%;">
    <div class="gridWrapper">
        <div style="width:auto;" class="tb-table">
            <div class="tb-row-titles">
                <div class="tb-th" data-tb-th-col="0" style="width: 49%;">
                    <span class="m-r-sm">Title</span>
                    % if sort == 'title':
                        <a href=${"?page=1" + query_params['q'] + '&sort=title'}><i class="fa fa-chevron-up asc-button m-r-xs fg-file-links "></i></a>
                    % else:
                        <a href=${"?page=1" + query_params['q'] + '&sort=title'}><i class="fa fa-chevron-up asc-button m-r-xs tb-sort-inactive"></i></a>
                    % endif
                    % if sort == '-title':
                        <a href=${"?page=1" + query_params['q'] + '&sort=-title'}><i class="fa fa-chevron-down desc-btn fg-file-links"></i></a>
                    % else:
                        <a href=${"?page=1" + query_params['q'] + '&sort=-title'}><i class="fa fa-chevron-down desc-btn tb-sort-inactive"></i></a>
                    % endif
                </div>
                <div class="tb-th" data-tb-th-col="1" style="width: 9%">
                    <span class="m-r-sm">Author</span>
                    % if sort == 'author':
                        <a href=${"?page=1" +  query_params['q'] + '&sort=author'}><i class="fa fa-chevron-up asc-btn m-r-xs fg-file-links"></i></a>
                    % else:
                        <a href=${"?page=1" +  query_params['q'] + '&sort=author'}><i class="fa fa-chevron-up asc-btn m-r-xs tb-sort-inactive"></i></a>
                    % endif
                    % if sort == '-author':
                        <a href=${"?page=1" +  query_params['q'] + '&sort=-author'}><i class="fa fa-chevron-down desc-btn fg-file-links"></i></a>
                    % else:
                        <a href=${"?page=1" +  query_params['q'] + '&sort=-author'}><i class="fa fa-chevron-down desc-btn tb-sort-inactive"></i></a>
                    % endif
                </div>
                <div class="tb-th" data-tb-th-col="2" style="width: 11%">
                    <span class="m-r-sm">Category</span>
                    % if sort == 'category':
                        <a href=${"?page=1" +  query_params['q'] + '&sort=category'}><i class="fa fa-chevron-up asc-btn m-r-xs fg-file-links"></i></a>
                    % else:
                        <a href=${"?page=1" +  query_params['q'] + '&sort=category'}><i class="fa fa-chevron-up asc-btn m-r-xs tb-sort-inactive"></i></a>
                    % endif
                    % if sort == '-category':
                        <a href=${"?page=1" +  query_params['q'] + '&sort=-category'}><i class="fa fa-chevron-down desc-btn fg-file-links"></i></a>
                    % else:
                        <a href=${"?page=1" +  query_params['q'] + '&sort=-category'}><i class="fa fa-chevron-down desc-btn tb-sort-inactive"></i></a>
                    % endif
                </div>
                <div class="tb-th" data-tb-th-col="3" style="width: 14%">
                    <span class="m-r-sm">Date Created</span>
                    % if sort == 'created':
                        <a href=${"?page=1" +  query_params['q'] + '&sort=created'}><i class="fa fa-chevron-up asc-btn m-r-xs fg-file-links"></i></a>
                    % else:
                        <a href=${"?page=1" +  query_params['q'] + '&sort=created'}><i class="fa fa-chevron-up asc-btn m-r-xs tb-sort-inactive"></i></a>
                    % endif
                    % if sort == '-created':
                        <a href=${"?page=1" +  query_params['q'] + '&sort=-created'}><i class="fa fa-chevron-down desc-btn fg-file-links"></i></a>
                    % else:
                        <a href=${"?page=1" +  query_params['q'] + '&sort=-created'}><i class="fa fa-chevron-down desc-btn tb-sort-inactive"></i></a>
                    % endif
                </div>
                <div class="tb-th" data-tb-th-col="4" style="width: 13%">
                    <span class="m-r-sm">Downloads</span>
                    % if sort == 'downloads':
                        <a href=${"?page=1" +  query_params['q'] + '&sort=downloads'}><i class="fa fa-chevron-up asc-btn m-r-xs fg-file-links"></i></a>
                    % else:
                        <a href=${"?page=1" +  query_params['q'] + '&sort=downloads'}><i class="fa fa-chevron-up asc-btn m-r-xs tb-sort-inactive"></i></a>
                    % endif
                    % if sort == '-downloads':
                        <a href=${"?page=1" +  query_params['q'] + '&sort=-downloads'}><i class="fa fa-chevron-down desc-btn fg-file-links"></i></a>
                    % else:
                        <a href=${"?page=1" +  query_params['q'] + '&sort=-downloads'}><i class="fa fa-chevron-down desc-btn tb-sort-inactive"></i></a>
                    % endif
                </div>
            </div>
        </div>
    </div>
</div>

% if not data:
    <div class="tb-no-results" style="border-left:1px solid #eee; border-right: 1px solid #eee;">
        No results found for this search term.
    </div>
% endif

<div id="grid" style="width:100%; height:500px;">
    <div class="spinner-loading-wrapper">
        <div class="ball-scale ball-scale-blue">
            <div></div>
        </div>
    </div>
</div>

% if page.has_other_pages():
    <div class="pull-right">
        <ul class="pagination">
            % if page.has_previous():
                <li><a href=${"?page=" + str(page.previous_page_number()) + query_params['q'] + query_params['sort']}>&laquo;</a></li>
            % else:
                <li class="disabled"><span>&laquo;</span></li>
            % endif
            % for i in pagination:
                % if page.number == i:
                    <li class="active"><span>${ i } <span class="sr-only">(current)</span></span></li>
                % elif i == '...':
                    <li> <span>${i} <span> </li>
                % else:
                    <li><a href=${"?page=" + str(i) + query_params['q'] + query_params['sort']}>${ i }</a></li>
                % endif
            % endfor
            % if page.has_next():
                <li><a href=${"?page=" + str(page.next_page_number()) + query_params['q'] + query_params['sort']}>&raquo;</a></li>
            % else:
                <li class="disabled"><span>&raquo;</span></li>
            % endif
        </ul>
    </div>
% endif

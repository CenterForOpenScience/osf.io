User: ${user.fullname} (${user.username}) [${user._id}]

Tried to register ${src.title} (${src.url}) [${src._id}], but the archive task failed when copying files. At least one file selected in the registration schema was moved or deleted in between its selection and archival. 

% for missing in results['missing_files']:
File name: ${missing['file_name']}
Question: ${missing['question_title']}
% endfor

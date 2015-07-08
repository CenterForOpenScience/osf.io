# Autosaving and submit process
- [X] Show the Submit button to submit for approval
- [X] Show which fields are required on submit (if required fields are not filled in there will be an error)
- [X] Autosaving functionality
- [X] Show no indication of which field have been completed (i.e. no green/yellow)

# Routes needed
- [X] Create new route `/asdfg/registrations/<uid>`

# Preview tab
- [ ] When "New Registration" is clicked on the `Draft Registration` taken to a `Preview` tab
- [ ] `Preview` tab has a dropdown (or other select method) to choose a schema
- [ ] On schema selection, displays a "Start registration" button, a description at top, and the schema in read-only mode
- [ ] When "Start registration" is clicked, create uid and redirect to new page using new route above

# File picker
- [x] Show only OSF storage
- [x] Have two options:
  * upload file - focuses on osf storage originally
  * select file from project
- [ ] Copy from OSF saved to root (I'm not totally clear on what this means -Lauren)
- [x] If upload then upload to outer OSF storage of project (where the original focus is)
- [x] Show (or enable) upload/select button once a file has been selected (currently selecting by clicking on row)
- [x] Save path to schema data
- [x] Display what file has been uploaded/selected

# Time bugs
- [ ] Last saved: local time with GMT in hover
- [ ] Time started the same ^
- [ ] located on the editor page as well as the `Draft Registrations` tab
- [ ] Show no text -- just show time i.e. get rid of "2 days ago" etc.

# Radio buttons
- [ ] Take out check -- make it look like a radio button
- [ ] Button to left of option text

# Schema typos
- [X] Fix typos and strange characters from showing up in schemas

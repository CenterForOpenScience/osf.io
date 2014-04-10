CONSUMER_KEY = 'changeme'
CONSUMER_SECRET = 'changeme'





POSSIBLE_ACTIONS =['project_created',
        'node_created',
        'wiki_updated',
        'contributor_added',
        'tag_added',
        'edit_title',
        'edit_description',
        'project_registered',
        'file_added',
        'file_updated',
    'node_forked'
 ]

#Default tweet messages for log events
DEFAULT_MESSAGES = {'project_created_message':'Created project: ',
                    'node_created_message': 'Created a project node',
                    'wiki_updated_message': 'Updated the wiki with: ',
                    'contributor_added_message': ' Added a project contributor!',
                    'tag_added_message': 'Added tag {tag_name} to our project',
                    'edit_title_message': 'Changed project title from {old_title} to {new_title}',
                    'edit_description_message': 'Changed project description to {new_desc}',
                    'project_registered_message': 'Just registered a new project!',
                    'file_added_message':' Just added {file_name} to our project',
                    'file_updated_message': 'Just updated a file',
                    'node_forked_message': 'Just forked a node',

}
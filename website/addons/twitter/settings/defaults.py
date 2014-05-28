CONSUMER_KEY = 'changeme'
CONSUMER_SECRET = 'changeme'





POSSIBLE_ACTIONS = [
        'project_created',
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
DEFAULT_MESSAGES = {'project_created_message':'We just created a new project ',
                    'node_created_message': 'We just created a project node',
                    'wiki_updated_message': 'We updated the wiki with: ',
                    'contributor_added_message': ' We added a project contributor',
                    'tag_added_message': 'We added tag {tag_name} to our project',
                    'edit_title_message': 'We changed the project title from {old_title} to {new_title}',
                    'edit_description_message': 'We changed the project description to {new_desc}',
                    'project_registered_message': 'We just registered a new project',
                    'file_added_message':' We just added {file_name} to our project',
                    'file_updated_message': 'We just updated a file',
                    'node_forked_message': 'We just forked a node',
}
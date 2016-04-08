
var logActions = {
    'box_file_added' : '${user} added a ${file} to Box in ${node}',
    'box_folder_created' : '${user} created folder ${path} in Box in ${node}',
    'box_file_updated' : '${user} updated file ${path} in Box in ${node}',
    'box_file_removed' : '${user} removed ${path} from Box in ${node}',
    'box_folder_selected': '${user} linked Box folder ${folder} to ${node}',
    'box_node_deauthorized' : '${user} deauthorized the Box addon for ${node}',
    'box_node_authorized' : '${user} authorized the Box addon for ${node}'
};

module.exports = logActions;
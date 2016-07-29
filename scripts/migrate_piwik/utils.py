from scripts.migrate_piwik import settings

def get_dir_for(phase):
    return '/'.join([
        settings.OUTPUT_DIR,
        settings.PHASES[phase.upper()]['DIR'],
    ])

def get_history_run_id_for(phase):
    history = get_history_for(phase, 'r')
    return history.readline().replace(settings.RUN_HEADER, '').rstrip()

def get_history_for(phase, mode):
    filename = '/'.join([get_dir_for(phase), settings.HISTORY_FILENAME])
    return open(filename, mode)

def get_complaints_run_id_for(phase):
    complaints = get_complaints_for(phase, 'r')
    return complaints.readline().replace(settings.RUN_HEADER, '').rstrip()

def get_complaints_for(phase, mode):
    filename = '/'.join([get_dir_for(phase), settings.COMPLAINTS_FILENAME])
    return open(filename, mode)

def get_batch_count():
    history_file = get_history_for('transform02', 'r')
    return int(history_file.readlines()[-1].replace(settings.BATCH_HEADER, '').rstrip())

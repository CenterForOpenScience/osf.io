from website.app import setup_django
setup_django()


from osf.models import Registration, RegistrationSchema
from website.project.tasks import update_node_share
import progressbar

 # To run: docker-compose run --rm web python -m scripts.remove_after_use.update_as_predicted_share
def main():
    """
    Sends AsPredicted registrations to SHARE (schema has been renamed)

    Run AFTER data migration which renames AsPredicted Preregistration => Preregistration Template from AsPredicted.org
    """
    schema = RegistrationSchema.objects.get(name='Preregistration Template from AsPredicted.org')
    registrations = Registration.objects.filter(registered_schema=schema)
    progress_bar = progressbar.ProgressBar(maxval=registrations.count()).start()
    for i, reg in enumerate(registrations, 1):
        progress_bar.update(i)
        update_node_share(reg)
    progress_bar.finish()

if __name__ == '__main__':
    main()

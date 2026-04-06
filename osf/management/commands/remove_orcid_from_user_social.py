from django.db.models.expressions import RawSQL
from osf.models import OSFUser


def remove_orcid_from_user_social():
    OSFUser.objects.filter(social__has_key='orcid').update(social=RawSQL("""social #- '{orcid}'""", []))

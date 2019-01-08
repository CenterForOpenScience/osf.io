from osf.models.base import BaseModel
from osf.utils.fields import LowercaseCharField

class BlacklistedEmailDomain(BaseModel):
    domain = LowercaseCharField(max_length=255, unique=True, db_index=True)

    def __unicode__(self):
        return self.domain

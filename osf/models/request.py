from django.db import models

from .base import BaseModel, ObjectIDMixin
from osf.utils.workflows import RequestTypes, DefaultStates
from osf.utils.machines import NodeRequestMachine, PreprintRequestMachine


class AbstractRequest(BaseModel, ObjectIDMixin):
    class Meta:
        abstract = True

    request_type = models.CharField(max_length=31, choices=RequestTypes.choices(legacy=True))
    creator = models.ForeignKey('OSFUser', related_name='submitted_%(class)s', on_delete=models.CASCADE)
    comment = models.TextField(null=True, blank=True)

    # NOTE: machine_state should rarely/never be modified directly -- use the state transition methods below
    machine_state = models.CharField(max_length=15, db_index=True, choices=DefaultStates.choices(), default=DefaultStates.INITIAL.value)

    date_last_transitioned = models.DateTimeField(null=True, blank=True, db_index=True)

    @property
    def target(self):
        raise NotImplementedError()


class NodeRequest(AbstractRequest):
    """ Request for Node Access
    """
    target = models.ForeignKey('AbstractNode', related_name='requests', on_delete=models.CASCADE)

    @property
    def MachineClass(self):
        return NodeRequestMachine

    @property
    def States(self):
        return DefaultStates


class PreprintRequest(AbstractRequest):
    """ Request for Preprint Withdrawal
    """
    target = models.ForeignKey('Preprint', related_name='requests', on_delete=models.CASCADE)

    @property
    def MachineClass(self):
        return PreprintRequestMachine

    @property
    def States(self):
        return DefaultStates

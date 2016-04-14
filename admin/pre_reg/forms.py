import itertools

from django import forms

from admin.pre_reg.utils import get_prereg_reviewers


class DraftRegistrationForm(forms.Form):

    proof_of_publication = forms.ChoiceField(
        label="Proof of publication",
        choices=(
            ("not_submitted", "Published Article Not Yet Submitted"),
            ("submitted", "Published Article Submitted"),
            ("under_review", "Published Article Under Review"),
            ("approved", "Published Article Approved"),
            ("rejected", "Published Article Rejected"),
        )
    )
    payment_sent = forms.BooleanField(
        label="Payment sent",
        required=False
    )
    assignee = forms.ChoiceField(
        label="Assignee",
        choices=list(),
        required=False,
    )

    notes = forms.CharField(
        label="Notes",
        widget=forms.Textarea(
            attrs={
                'class': 'prereg-form-notes'
            }
        ),
        required=False
    )

    approve_reject = forms.ChoiceField(
        label='Action',
        choices=(
            ('approve', 'Approve'),
            ('reject', 'Reject'),
        ),
        required=False,
        widget=forms.RadioSelect(),
    )

    def __init__(self, *args, **kwargs):
        prereg_reviewers = itertools.chain(
            ((None, 'None'), ), get_prereg_reviewers())
        self.base_fields['assignee'] = forms.ChoiceField(
            choices=prereg_reviewers, required=False)
        super(DraftRegistrationForm, self).__init__(*args, **kwargs)

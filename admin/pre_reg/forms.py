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
        label="Payment sent"
    )
    notes = forms.CharField(
        label="Notes",
        widget=forms.Textarea(
            attrs={
                'style': 'height: 50px;'
            }
        )
    )
    assignee = forms.ChoiceField(
        label="Assignee",
        choices=get_prereg_reviewers
    )


DraftRegistrationFormset = forms.formset_factory(DraftRegistrationForm)

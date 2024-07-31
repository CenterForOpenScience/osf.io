from django import forms

from osf.models import Preprint
from osf.utils.workflows import ReviewStates

class ChangeProviderForm(forms.ModelForm):
    class Meta:
        model = Preprint
        fields = ('provider',)


class MachineStateForm(forms.ModelForm):
    class Meta:
        model = Preprint
        fields = ('machine_state',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.is_public:
            self.fields['machine_state'].widget.attrs['disabled'] = 'disabled'
        else:
            if self.instance.machine_state == ReviewStates.INITIAL.db_name:
                self.fields['machine_state'].choices = [
                    (ReviewStates.INITIAL.value, ReviewStates.INITIAL.value),
                    (ReviewStates.PENDING.value, ReviewStates.PENDING.value),
                ]
            else:
                # Disabled Option you are on
                self.fields['machine_state'].widget.attrs['disabled'] = 'disabled'
                self.fields['machine_state'].choices = [
                    (self.instance.machine_state.title(), self.instance.machine_state)
                ]

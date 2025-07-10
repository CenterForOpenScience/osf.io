from rest_framework import serializers as ser

class FrequencyField(ser.ChoiceField):
    def __init__(self, **kwargs):
        super().__init__(choices=['none', 'instantly', 'daily', 'weekly', 'monthly'], **kwargs)

    def to_representation(self, frequency: str):
        return frequency or 'none'

    def to_internal_value(self, freq):
        return super().to_internal_value(freq)

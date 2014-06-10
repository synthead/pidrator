from django.forms import ModelForm

from pidrator.models import Irrigator


class IrrigatorForm(ModelForm):
  class Meta:
    model = Irrigator
    fields = [
        "lowest_moisture",
        "watering_seconds",
        "timeout_seconds",
        "enabled"
    ]

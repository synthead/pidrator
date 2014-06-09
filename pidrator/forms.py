from django.forms import ModelForm

from pidrator.models import Irrigator


class IrrigatorForm(ModelForm):
  class Meta:
    model = Irrigator
    fields = [
        "desired_moisture",
        "watering_seconds",
        "timeout_seconds",
        "upper_deviation",
        "lower_deviation",
        "enabled"
    ]

import json

from django.shortcuts import render
from django.http import HttpResponse

from django.forms.models import modelformset_factory
from pidrator.forms import IrrigatorForm

from pidrator.models import Irrigator


IrrigatorModelFormSet = modelformset_factory(
    Irrigator, form=IrrigatorForm, extra=0)


def Index(request):
  context = {"irrigator_formset": IrrigatorModelFormSet}

  return render(request, "index.html", context)


def UpdateIrrigator(request):
  irrigator_formset = IrrigatorModelFormSet(request.POST)
  irrigator_formset.save()

  return HttpResponse("Submitted.")

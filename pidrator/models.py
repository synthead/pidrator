from django.db.models import Model

from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DecimalField
from django.db.models import FloatField
from django.db.models import ForeignKey
from django.db.models import IntegerField

from django.db.models.signals import post_save
from django.dispatch import receiver

from omnibus.api import publish

from pidrator.hardware_controller import CheckIrrigators

from pidrator.validators import ValidatePercentage
from pidrator.validators import ValidateSensorValue
from pidrator.validators import ValidatePositiveFloat


class Relay(Model):
  name = CharField(default="Relay", max_length=255)
  enabled = BooleanField(default=True)

  channel = IntegerField(unique=True)
  actuated = BooleanField(default=False)

  class Meta:
    db_table = "relay"


class Sensor(Model):
  name = CharField(default="Sensor", max_length=255)
  enabled = BooleanField(default=True)

  spi_port = IntegerField(unique=True)
  spi_device = IntegerField(unique=True)
  channel = IntegerField()

  moisture = IntegerField(null=True)
  calibrate_low = IntegerField(default=0, validators=[ValidateSensorValue])
  calibrate_high = IntegerField(default=1023, validators=[ValidateSensorValue])

  class Meta:
    db_table = "sensor"


class Irrigator(Model):
  relay = ForeignKey(Relay, unique=True)
  sensor = ForeignKey(Sensor)

  name = CharField(default="Irrigator", max_length=255)
  enabled = BooleanField(default=False)

  lowest_moisture = DecimalField(
      max_digits=4, decimal_places=1, default=20,
      validators=[ValidatePercentage])
  in_watering_cycle = BooleanField(default=False)
  watering_seconds = FloatField(default=10, validators=[ValidatePositiveFloat])
  timeout_seconds = FloatField(default=50, validators=[ValidatePositiveFloat])

  class Meta:
    db_table = "irrigator"


@receiver(post_save, sender=Irrigator)
def IrrigatorUpdated(sender, **kwargs):
  if (kwargs["update_fields"] and
      kwargs["update_fields"] == ["in_watering_cycle"]):
    publish(
        "pidrator", "irrigator-%d" % kwargs["instance"].pk,
        {"in_watering_cycle": kwargs["instance"].in_watering_cycle})
  else:
    CheckIrrigators.delay(pk=kwargs["instance"].pk)


@receiver(post_save, sender=Sensor)
def SensorUpdated(sender, **kwargs):
  CheckIrrigators.delay(sensor=kwargs["instance"])
  publish(
      "pidrator", "sensor-%d" % kwargs["instance"].pk,
      {"moisture": None if not kwargs["instance"].moisture else
           float(kwargs["instance"].moisture)})


@receiver(post_save, sender=Relay)
def RelayUpdated(sender, **kwargs):
  publish(
      "pidrator", "relay-%d" % kwargs["instance"].pk,
      {"actuated": kwargs["instance"].actuated})

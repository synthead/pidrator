from django.db.models import Model
from django.db.models import CharField
from django.db.models import BooleanField
from django.db.models import IntegerField
from django.db.models import DecimalField
from django.db.models import ForeignKey

from django.db.models.signals import post_save
from django.dispatch import receiver

from omnibus.api import publish

from pidrator.hardware_controller import CheckIrrigators


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
  channel = IntegerField(unique=True)

  moisture = IntegerField(null=True)
  calibrate_low = IntegerField(default=0)
  calibrate_high = IntegerField(default=1023)

  class Meta:
    db_table = "sensor"


class Irrigator(Model):
  relay = ForeignKey(Relay, unique=True)
  sensor = ForeignKey(Sensor)

  name = CharField(default="Irrigator", max_length=255)
  enabled = BooleanField(default=False)

  in_watering_cycle = BooleanField(default=False)
  watering_seconds = IntegerField(default=10)
  timeout_seconds = IntegerField(default=60)
  
  desired_moisture = DecimalField(
      max_digits=3, decimal_places=1, default=20)
  lower_deviation = DecimalField(
      max_digits=3, decimal_places=1, default=5)
  upper_deviation = DecimalField(
      max_digits=3, decimal_places=1, default=5)

  class Meta:
    db_table = "irrigator"


@receiver(post_save, sender=Irrigator)
def IrrigatorUpdated(sender, **kwargs):
  CheckIrrigators.delay()


@receiver(post_save, sender=Sensor)
def SensorUpdated(sender, **kwargs):
  sensor = kwargs["instance"]

  CheckIrrigators.delay(sensor)
  publish(
      "pidrator", "sensor-%d" % sensor.pk,
      {"moisture": None if not sensor.moisture else float(sensor.moisture)})


@receiver(post_save, sender=Relay)
def RelayUpdated(sender, **kwargs):
  sensor = kwargs["instance"]

  publish(
      "pidrator", "relay-%d" % sensor.pk,
      {"actuated": str(sensor.actuated)})

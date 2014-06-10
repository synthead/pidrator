from pidrator.celery import celery_pidrator

from celery.signals import celeryd_init
from celery.signals import worker_shutdown

from celery.utils.log import get_task_logger

from pidrator.settings import PIDRATOR_TESTING_WITHOUT_HARDWARE


logger = get_task_logger(__name__)


@celeryd_init.connect
def CelerydInit(**kwargs):
  from celery.task.control import discard_all
  discard_all()

  if not PIDRATOR_TESTING_WITHOUT_HARDWARE:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)


@worker_shutdown.connect
def WorkerShutdown(**kwargs):
  from celery import chain
  from pidrator.models import Relay
  from pidrator.models import Irrigator

  chain(
      ActuateRelay.si(relay, False) for relay in
      Relay.objects.filter(enabled=True)
  ).apply()

  chain(
      SetWateringCycle.si(irrigator, False) for irrigator in
      Irrigator.objects.filter(in_watering_cycle=True)
  ).apply()


@celery_pidrator.task
def UpdateEnabledSensors():
  from celery import chain
  from pidrator.models import Sensor
  chain(
      UpdateSensor.si(sensor) for sensor in Sensor.objects.filter(enabled=True)
  ).apply_async()


@celery_pidrator.task
def UpdateSensor(sensor):
  if PIDRATOR_TESTING_WITHOUT_HARDWARE:
    import random
    moisture = random.randint(0, 1023)
  else:
    import spidev
    spi = spidev.SpiDev()
    spi.open(sensor.spi_port, sensor.spi_device)
    adc = spi.xfer2([1, (8 + sensor.channel) << 4, 0])
    moisture = int(((adc[1] & 3) << 8) + adc[2])

  if moisture != sensor.moisture:
    sensor.moisture = moisture
    sensor.save()
    logger.warning("Updated sensor \"%s\" to %d.", sensor.name, sensor.moisture)


@celery_pidrator.task
def ActuateRelay(relay, actuated):
  if not PIDRATOR_TESTING_WITHOUT_HARDWARE:
    import RPi.GPIO as GPIO
    GPIO.setup(relay.channel, GPIO.OUT, initial=actuated)

  if relay.actuated is not actuated:
    relay.actuated = actuated
    relay.save()
    logger.warning(
        "Relay \"%s\" on channel %d %s.", relay.name, relay.channel,
        ("deactuated", "actuated")[relay.actuated])


@celery_pidrator.task
def WateringCycle(irrigator):
  from celery import chain
  chain(
      SetWateringCycle.si(irrigator, True),
      ActuateRelay.si(irrigator.relay, True),
      ActuateRelay.subtask(
          (irrigator.relay, False),
          countdown=irrigator.watering_seconds,
          immutable=True),
      SetWateringCycle.subtask(
          (irrigator, False),
          countdown=irrigator.timeout_seconds,
          immutable=True)
  ).apply_async()


@celery_pidrator.task
def SetWateringCycle(irrigator, in_watering_cycle):
  irrigator.in_watering_cycle = in_watering_cycle
  irrigator.save(update_fields=["in_watering_cycle"])
  logger.warning(
      "Watering cycle %s for \"%s\".",
      ("finished", "started")[in_watering_cycle], irrigator.name)


@celery_pidrator.task
def CheckIrrigators(**filter_args):
  from pidrator.models import Irrigator
  from django.db.models import F
  from django.db.models import Q

  for irrigator in Irrigator.objects.filter(
      Q(in_watering_cycle=False) &
      Q(lowest_moisture__gte=(
          (F("sensor__moisture") - F("sensor__calibrate_low"))
          / F("sensor__calibrate_high") * 100)) &
      Q(enabled=True) &
      Q(relay__enabled=True) &
      Q(sensor__enabled=True),
      **filter_args):
    WateringCycle.delay(irrigator)

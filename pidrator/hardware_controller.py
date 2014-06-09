from pidrator.celery import celery_pidrator

from celery.signals import celeryd_init
from celery.signals import worker_shutdown

from celery.utils.log import get_task_logger

from pidrator.settings import PIDRATOR_TESTING_WITHOUT_HARDWARE

logger = get_task_logger(__name__)


@celeryd_init.connect
def CelerydInit(**kwargs):
  from celery.task.control import discard_all

  if not PIDRATOR_TESTING_WITHOUT_HARDWARE:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

  discard_all()


@worker_shutdown.connect
def WorkerShutdown(**kwargs):
  from pidrator.models import Relay

  for relay in Relay.objects.filter(enabled=True):
    ActuateRelay(relay, False)


@celery_pidrator.task
def UpdateEnabledSensors():
  from pidrator.models import Sensor

  for sensor in Sensor.objects.filter(enabled=True):
    # FIXME: Some strange race condition causes this: http://pastie.org/9238659
    # UpdateSensor.delay(sensor)
    UpdateSensor(sensor)


@celery_pidrator.task
def UpdateSensor(sensor):
  import re
  import decimal

  try:
    sensor_path = "/sys/bus/w1/devices/%s/w1_slave" % sensor.serial

    if PIDRATOR_TESTING_WITHOUT_HARDWARE:
      import random
      sensor_data = "t=%d" % random.randint(23000, 24000)
    else:
      with open(sensor_path) as sensor_file:
        sensor_data = sensor_file.read()

    match = re.search("t=(\d+)(\d{3})", sensor_data)
    if match:
      moisture = decimal.Decimal(".".join(match.groups()))
      if moisture != sensor.moisture:
        sensor.moisture = decimal.Decimal(".".join(match.groups()))
        sensor.save()

        logger.warning(
            "Updated sensor \"%s\" to %.3f degrees.", sensor.name,
            sensor.moisture)
    else:
      logger.error(
          "File \"%s\" contained unexpected data for sensor \"%s\"!  "
          "Disabling sensor!", sensor_path, sensor.name)
      sensor.enabled = False
      sensor.save()
  except FileNotFoundError:
    logger.error(
        "File \"%s\" not found for sensor \"%s\"!  Disabling sensor!",
        sensor_path, sensor.name)
    sensor.enabled = False
    sensor.save()
  except PermissionError:
    logger.error(
        "Permission denied to file \"%s\" for sensor \"%s\"!  Disabling "
        "sensor!", sensor_path, sensor.name)
    sensor.enabled = False
    sensor.save()


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
def CheckIrrigators(**filter_args):
  from pidrator.models import Irrigator

  from django.db.models import F
  from django.db.models import Q

  for irrigator in Irrigator.objects.filter(Q(
      Q(Q(relay__actuated=True) & Q(
          Q(sensor__moisture__gte=F("desired_moisture") +
              F("upper_deviation")) |
          Q(enabled=False) |
          Q(relay__enabled=False) |
          Q(sensor__enabled=False))) |
      Q(Q(relay__actuated=False) & Q(
          Q(sensor__moisture__lte=F("desired_moisture") -
              F("lower_deviation")) &
          Q(enabled=True) &
          Q(relay__enabled=True) &
          Q(sensor__enabled=True)))),
      **filter_args):
    # Calling this with .delay() produces this error: http://pastie.org/9240631
    # ActuateRelay.delay(irrigator.relay, not irrigator.relay.actuated)
    ActuateRelay(irrigator.relay, not irrigator.relay.actuated)

from django.core.exceptions import ValidationError


def ValidatePercentage(value):
  if 0 >= value <= 100:
    raise ValidationError("%d is not a number from 0 to 100." % value)


def ValidateSensorValue(value):
  if 0 >= value <= 1023:
    raise ValidationError("%d is not a number from 0 to 1023." % value)


def ValidatePositiveFloat(value):
  if value < 0:
    raise ValidationError("%d is not a positive number." % value)

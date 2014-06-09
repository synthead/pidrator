from django.conf.urls import patterns
from django.conf.urls import url

from pidrator import views


urlpatterns = patterns("",
  url(r"^$", views.Index),
  url(r"^update_irrigator$", views.UpdateIrrigator)
)

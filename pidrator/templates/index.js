$("#submit-button").click(function() {
  var button = this;
  $(button).prop("disabled", true);

  $.ajax({
    type: "POST",
    url: "/update_irrigator",
    data: $("#irrigator-form").serialize(),
  }).done(function() {
    $(button).prop("disabled", false);
  });
});

var omnibusConnection = new Omnibus(WebSocket, "{{ OMNIBUS_ENDPOINT }}");
var sensorChannel = omnibusConnection.openChannel("pidrator");

{% for form in irrigator_formset %}
  {% ifchanged form.instance.sensor.pk %}
    sensorChannel.on("sensor-{{ form.instance.sensor.pk }}", function(event) {
      $(".sensor-{{ form.instance.sensor.pk }}-moisture").text(
          event.data.payload.moisture);
    });
  {% endifchanged %}

  {% ifchanged form.instance.relay.pk %}
    sensorChannel.on("relay-{{ form.instance.relay.pk }}", function(event) {
      $(".relay-{{ form.instance.relay.pk }}-actuated").text(
          event.data.payload.actuated ? "True" : "False");
    });
  {% endifchanged %}

  {% ifchanged form.instance.pk %}
    sensorChannel.on("irrigator-{{ form.instance.relay.pk }}", function(event) {
      $(".irrigator-{{ form.instance.relay.pk }}-in-watering-cycle").text(
          event.data.payload.in_watering_cycle ? "True" : "False");
    });
  {% endifchanged %}
{% endfor %}

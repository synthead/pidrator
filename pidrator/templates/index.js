$(".irrigator-submit").click(function() {
  var button = this;
  $(button).prop("disabled", true);

  $.ajax({
    type: "POST",
    url: "/update_irrigator",
    data: $(button.parentNode.parentNode).serialize(),
  }).done(function() {
    $(button).prop("disabled", false);
  });
});

var omnibusConnection = new Omnibus(
    WebSocket,
    "{{ OMNIBUS_ENDPOINT }}"
);

var sensorChannel = omnibusConnection.openChannel("pidrator");

var sensor = "sensor-1";  // FIXME: make dynmaic
sensorChannel.on(sensor, function(event) {
  $("." + sensor + "-moisture").text(event.data.payload.moisture);
});

var relay = "relay-1";  // FIXME: make dynmaic
sensorChannel.on(relay, function(event) {
  $("." + relay + "-actuated").text(event.data.payload.actuated);
});

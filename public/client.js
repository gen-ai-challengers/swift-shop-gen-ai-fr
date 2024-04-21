// get DOM elements
var dataChannelLog = document.getElementById("data-channel"),
  iceConnectionLog = document.getElementById("ice-connection-state"),
  iceGatheringLog = document.getElementById("ice-gathering-state"),
  signalingLog = document.getElementById("signaling-state");

// peer connection
var pc = null;

// data channel
var dc = null,
  dcInterval = null;
  var startTime;

function createPeerConnection() {
  // create an RTCPeerConnection
  console.log("1.1 Creating RTCPeerConnection", new Date().getTime() - startTime);
  var config = {
    sdpSemantics: "unified-plan",
  };

  if (document.getElementById("use-stun").checked) {
    console.log("Using STUN server");
    let iceServers=[];
    try {
      const text = document.getElementById("use-stun-value").value.trim();
      if (!text) {
        throw new Error("empty value");
      }
      console.log("STUN/TURN server value:",text);
      
      iceServers = eval(text);
      console.log("STUN/TURN server value after parse:",iceServers);
      if (!Array.isArray(iceServers)) {
        throw new Error("iceServers not an array");
      }
      
    } catch (error) {
      console.error("Invalid STUN/TURN server value",error);
      alert("Invalid STUN/TURN server value"+error);
      document.getElementById("start").style.display = "inline-block";
      return;
    }
    config.iceServers = iceServers
  }

  console.log("RTCPeerConnection configuration:", config);
  try{
  pc = new RTCPeerConnection(config);
  }catch(e){
    console.error("Error creating RTCPeerConnection",e);
    alert("Error creating RTCPeerConnection"+e);
    document.getElementById("start").style.display = "inline-block";
    return;
  }
  if (!pc) {
    console.error("Failed to create RTCPeerConnection");
    alert("Failed to create RTCPeerConnection");
    document.getElementById("start").style.display = "inline-block";
    return;
  }
  console.log("RTCPeerConnection created", new Date().getTime() - startTime);

  // register some listeners to help debugging
  pc.addEventListener(
    "icegatheringstatechange",
    () => {
      console.log(" -> ICE gathering state change to:", pc.iceGatheringState,new Date().getTime() - startTime);
      iceGatheringLog.textContent += " -> " + pc.iceGatheringState;
    },
    false
  );
  iceGatheringLog.textContent = pc.iceGatheringState;

  pc.addEventListener(
    "iceconnectionstatechange",
    () => {
      console.log(" -> ICE connection state change to:", pc.iceConnectionState,new Date().getTime() - startTime);
      iceConnectionLog.textContent += " -> " + pc.iceConnectionState;
    },
    false
  );
  iceConnectionLog.textContent = pc.iceConnectionState;

  pc.addEventListener(
    "signalingstatechange",
    () => {
      console.log(" -> Signaling state change to:", pc.signalingState,new Date().getTime() - startTime);
      signalingLog.textContent += " -> " + pc.signalingState;
    },
    false
  );
  signalingLog.textContent = pc.signalingState;

  // connect audio / video
  pc.addEventListener("track", (evt) => {
    console.log("Got MediaStreamTrack:", evt.track, "from receiver:", evt.receiver,new Date().getTime() - startTime);
    if (evt.track.kind == "video")
      document.getElementById("video").srcObject = evt.streams[0];
    else document.getElementById("audio").srcObject = evt.streams[0];
  });

  return pc;
}

function enumerateInputDevices() {
  const populateSelect = (select, devices) => {
    let counter = 1;
    devices.forEach((device) => {
      const option = document.createElement("option");
      option.value = device.deviceId;
      option.text = device.label || "Device #" + counter;
      select.appendChild(option);
      counter += 1;
    });
  };

  navigator.mediaDevices
    .enumerateDevices()
    .then((devices) => {
      populateSelect(
        document.getElementById("audio-input"),
        devices.filter((device) => device.kind == "audioinput")
      );
      populateSelect(
        document.getElementById("video-input"),
        devices.filter((device) => device.kind == "videoinput")
      );
    })
    .catch((e) => {
      alert(e);
    });
}

function negotiate() {
  console.log("2 Negotiating", new Date().getTime() - startTime);
  return pc
    .createOffer()
    .then((offer) => {
      console.log("2 Setting local description", new Date().getTime() - startTime);
      return pc.setLocalDescription(offer);
    })
    .then(() => {
      console.log("2 Negotiation complete", new Date().getTime() - startTime);
      var offer = pc.localDescription;
      var codec;

      codec = document.getElementById("audio-codec").value;
      if (codec !== "default") {
        offer.sdp = sdpFilterCodec("audio", codec, offer.sdp);
      }

      codec = document.getElementById("video-codec").value;
      if (codec !== "default") {
        offer.sdp = sdpFilterCodec("video", codec, offer.sdp);
      }

      document.getElementById("offer-sdp").textContent = offer.sdp;
      console.log("2 Sending offer to server", new Date().getTime() - startTime);
      return fetch("/api/offer-fr/", {
        body: JSON.stringify({
          sdp: offer.sdp,
          type: offer.type,
          action: document.getElementById("video-transform").value,
        }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });
    })
    .then((response) => {
      console.log("2 Got answer from server", new Date().getTime() - startTime);
      return response.json();
    })
    .then((answer) => {
      console.log("Setting remote description");
      document.getElementById("answer-sdp").textContent = answer.sdp;
      return pc.setRemoteDescription(answer);
    })
    .catch((e) => {
      alert(e);
    });
}

function start() {
  startTime = new Date().getTime();
  document.getElementById("start").style.display = "none";

  console.log("1 Starting call", new Date().getTime() - startTime);
  pc = createPeerConnection();
  console.log("1.1 Peer connection created", new Date().getTime() - startTime);
  console.log("pc.iceConnectionState",pc.iceConnectionState, new Date().getTime() - startTime);
  console.log("pc.iceGatheringState",pc.iceGatheringState, new Date().getTime() - startTime);
  console.log("pc.signalingState",pc.signalingState, new Date().getTime() - startTime);

  var time_start = null;

  const current_stamp = () => {
    if (time_start === null) {
      time_start = new Date().getTime();
      return 0;
    } else {
      return new Date().getTime() - time_start;
    }
  };

  if (document.getElementById("use-datachannel").checked) {
    var parameters = JSON.parse(
      document.getElementById("datachannel-parameters").value
    );

    dc = pc.createDataChannel("chat", parameters);
    dc.addEventListener("close", () => {
      clearInterval(dcInterval);
      dataChannelLog.textContent += "- close\n";
    });
    dc.addEventListener("open", () => {
      dataChannelLog.textContent += "- open\n";
      dcInterval = setInterval(() => {
        var message = "ping " + current_stamp();
        dataChannelLog.textContent += "> " + message + "\n";
        dc.send(message);
      }, 1000);
    });
    dc.addEventListener("message", (evt) => {
      dataChannelLog.textContent += "< " + evt.data + "\n";

      if (evt.data.substring(0, 4) === "pong") {
        var elapsed_ms = current_stamp() - parseInt(evt.data.substring(5), 10);
        dataChannelLog.textContent += " RTT " + elapsed_ms + " ms\n";
      }
    });
  }

  // Build media constraints.

  const constraints = {
    audio: false,
    video: false,
  };

  if (document.getElementById("use-audio").checked) {
    const audioConstraints = {};

    const device = document.getElementById("audio-input").value;
    if (device) {
      audioConstraints.deviceId = { exact: device };
    }

    constraints.audio = Object.keys(audioConstraints).length
      ? audioConstraints
      : true;
  }

  if (document.getElementById("use-video").checked) {
    const videoConstraints = {};

    const device = document.getElementById("video-input").value;
    if (device) {
      videoConstraints.deviceId = { exact: device };
    }

    const resolution = document.getElementById("video-resolution").value;
    if (resolution) {
      const dimensions = resolution.split("x");
      videoConstraints.width = parseInt(dimensions[0], 0);
      videoConstraints.height = parseInt(dimensions[1], 0);
    }
    videoConstraints.frameRate = 10;

    constraints.video = Object.keys(videoConstraints).length
      ? videoConstraints
      : true;
  }

  // Acquire media and start negociation.

  if (constraints.audio || constraints.video) {
    if (constraints.video) {
      document.getElementById("media").style.display = "block";
    }
    navigator.mediaDevices.getUserMedia(constraints).then(
      
      (stream) => {
        console.log("pc.iceConnectionState",pc.iceConnectionState, new Date().getTime() - startTime);
        console.log("pc.iceGatheringState",pc.iceGatheringState, new Date().getTime() - startTime);
        console.log("pc.signalingState",pc.signalingState, new Date().getTime() - startTime);
        stream.getTracks().forEach((track) => {
          pc.addTrack(track, stream);
        });
        console.log("1.1 Media acquired", new Date().getTime() - startTime);
        return negotiate();
      },
      (err) => {
        alert("Could not acquire media: " + err);
      }
    );
  } else {
    console.log("1.1 No media selected", new Date().getTime() - startTime);
    negotiate();
  }
  console.log("Call started", new Date().getTime() - startTime);
  document.getElementById("stop").style.display = "inline-block";
}

function stop() {
  document.getElementById("stop").style.display = "none";
  document.getElementById("start").style.display = "inline-block";

  // close data channel
  if (dc) {
    dc.close();
  }

  // close transceivers
  if (pc.getTransceivers) {
    pc.getTransceivers().forEach((transceiver) => {
      if (transceiver.stop) {
        transceiver.stop();
      }
    });
  }

  // close local audio / video
  pc.getSenders().forEach((sender) => {
    sender.track.stop();
  });

  // close peer connection
  setTimeout(() => {
    pc.close();
  }, 500);
}

function sdpFilterCodec(kind, codec, realSdp) {
  var allowed = [];
  var rtxRegex = new RegExp("a=fmtp:(\\d+) apt=(\\d+)\r$");
  var codecRegex = new RegExp("a=rtpmap:([0-9]+) " + escapeRegExp(codec));
  var videoRegex = new RegExp("(m=" + kind + " .*?)( ([0-9]+))*\\s*$");

  var lines = realSdp.split("\n");

  var isKind = false;
  for (var i = 0; i < lines.length; i++) {
    if (lines[i].startsWith("m=" + kind + " ")) {
      isKind = true;
    } else if (lines[i].startsWith("m=")) {
      isKind = false;
    }

    if (isKind) {
      var match = lines[i].match(codecRegex);
      if (match) {
        allowed.push(parseInt(match[1]));
      }

      match = lines[i].match(rtxRegex);
      if (match && allowed.includes(parseInt(match[2]))) {
        allowed.push(parseInt(match[1]));
      }
    }
  }

  var skipRegex = "a=(fmtp|rtcp-fb|rtpmap):([0-9]+)";
  var sdp = "";

  isKind = false;
  for (var i = 0; i < lines.length; i++) {
    if (lines[i].startsWith("m=" + kind + " ")) {
      isKind = true;
    } else if (lines[i].startsWith("m=")) {
      isKind = false;
    }

    if (isKind) {
      var skipMatch = lines[i].match(skipRegex);
      if (skipMatch && !allowed.includes(parseInt(skipMatch[2]))) {
        continue;
      } else if (lines[i].match(videoRegex)) {
        sdp += lines[i].replace(videoRegex, "$1 " + allowed.join(" ")) + "\n";
      } else {
        sdp += lines[i] + "\n";
      }
    } else {
      sdp += lines[i] + "\n";
    }
  }

  return sdp;
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); // $& means the whole matched string
}

enumerateInputDevices();

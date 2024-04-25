// get DOM elements
var
  signalingLog

// peer connection
var pc = null;

// data channel
var dc = null,
  dcInterval = null,
  dcInterval2 = null;
var startTime;
var stopped = false;

function createPeerConnection() {
  // create an RTCPeerConnection
  console.log("1.1 Creating RTCPeerConnection", new Date().getTime() - startTime);
  var config = {
    sdpSemantics: "unified-plan",
    iceServers: [{
      urls: "turn:turn.genai.amprajin.in:3478",
      username: "genai",
      credential: "genai",
    }],
  };

  console.log("RTCPeerConnection configuration:", config);
  try {
    pc = new RTCPeerConnection(config);
  } catch (e) {
    console.error("Error creating RTCPeerConnection", e);
    alert("Error creating RTCPeerConnection" + e);
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
      console.log(" -> ICE gathering state change to:", pc.iceGatheringState, new Date().getTime() - startTime);
    },
    false
  );

  pc.addEventListener(
    "iceconnectionstatechange",
    () => {
      console.log(" -> ICE connection state change to:", pc.iceConnectionState, new Date().getTime() - startTime);
    },
    false
  );

  pc.addEventListener(
    "signalingstatechange",
    () => {
      console.log(" -> Signaling state change to:", pc.signalingState, new Date().getTime() - startTime);
    },
    false
  );

  pc.addEventListener("connectionstatechange", () => {
    console.log(" -> Connection state change to:", pc.connectionState, new Date().getTime() - startTime);
    if(pc.connectionState === "disconnected") {
      document.getElementById("media").style.display = "none";
      if (!stopped) {
        pc = createPeerConnection();
      }
    }
  })

  // not required 
  // connect audio / video
  pc.addEventListener("track", (evt) => {

    console.log("Got MediaStreamTrack:", evt.track, "from receiver:", evt.receiver, new Date().getTime() - startTime);
  });
  // responce from server
  pc.addEventListener("datachannel", (evt) => {
    console.log("Got DataChannel:", evt.channel, new Date().getTime() - startTime);
    dc = evt.channel;
    dc.addEventListener("close", () => {
      clearInterval(dcInterval2);
      console.log("DataChannel closed", new Date().getTime() - startTime);
    });
    dc.addEventListener("open", () => {
      console.log("DataChannel opened", new Date().getTime() - startTime);
      dcInterval2 = setInterval(() => {
        var message = "ping data 2";
        console.log("Sending DataChannel message:", message, new Date().getTime() - startTime);
        dc.send(message);
      }, 10000);
    });
    dc.addEventListener("message", (evt) => {
      console.log("Got DataChannel message:", evt.data, new Date().getTime() - startTime);
      if (evt.data.trim() === "stop") {
        console.log("Stopping", new Date().getTime() - startTime);
        stop()
      }
    });
  });
  pc.createDataChannel("events");
  console.log("DataChannel created", new Date().getTime() - startTime);

  return pc;
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
      // wait for ICE gathering to complete
      return new Promise((resolve) => {
        if (pc.iceGatheringState === "complete") {
          resolve();
        } else {
          function checkState() {
            if (pc.iceGatheringState === "complete") {
              pc.removeEventListener("icegatheringstatechange", checkState);
              resolve();
            }
          }
          pc.addEventListener("icegatheringstatechange", checkState);
        }
      });
    })
    
    .then(() => {
      console.log("2 Negotiation complete", new Date().getTime() - startTime);
      var offer = pc.localDescription;
      offer.sdp = sdpFilterCodec("video", "H264", offer.sdp);
      console.log("2 Sending offer to server", new Date().getTime() - startTime);
      const action = document.getElementById("video-transform").value
      console.log("action", action);
      const url = action == 'face_recognition' ? "/api/offer-fr/" : "/api/v1/users/me/add-face-offer/";
      console.log("url", url);
      return fetch(url, {
        body: JSON.stringify({
          sdp: offer.sdp,
          type: offer.type,
          action: action,
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
      console.log("answer", answer);
      document.getElementById("media").style.display = "block";
      document.getElementById("loading").style.display = "none";
      console.log("2 Setting remote description", new Date().getTime() - startTime);
      console.log("showing video", new Date().getTime() - startTime);
      return pc.setRemoteDescription(answer);
    })
    .catch((e) => {
      alert(e);
    });
}

function start() {
  document.getElementById("loading").style.display = "block";
  stopped = false;
  startTime = new Date().getTime();
  document.getElementById("start").style.display = "none";
  pc = createPeerConnection();

  console.log("1 Starting call", new Date().getTime() - startTime);
  
  console.log("1.1 Peer connection created", new Date().getTime() - startTime);
  console.log("pc.iceConnectionState", pc.iceConnectionState, new Date().getTime() - startTime);
  console.log("pc.iceGatheringState", pc.iceGatheringState, new Date().getTime() - startTime);
  console.log("pc.signalingState", pc.signalingState, new Date().getTime() - startTime);


  // Build media constraints.

  const constraints = {
    audio: false,
    video: {
      width: {
        min: 120,
        ideal: 320,
        max: 1024,
      },
      height: {
        min: 120,
        ideal: 240,
        max: 720,
      },
      frameRate: {
        min: 10,
        ideal: 15,
        max: 30,
      },
      facingMode: "user",
    }
  };


  // Acquire media and start negociation.

  navigator.mediaDevices.getUserMedia(constraints).then(

    (stream) => {
      console.log("pc.iceConnectionState", pc.iceConnectionState, new Date().getTime() - startTime);
      console.log("pc.iceGatheringState", pc.iceGatheringState, new Date().getTime() - startTime);
      console.log("pc.signalingState", pc.signalingState, new Date().getTime() - startTime);
      stream.getTracks().forEach((track) => {
        pc.addTrack(track, stream);
        if (track.kind == "video") {
          document.getElementById("video").srcObject = stream;
        }
      });
      console.log("1.1 Media acquired", new Date().getTime() - startTime);
      return negotiate();
    },
    (err) => {
      console.error("Error acquiring media:", err);
      document.getElementById("loading").style.display = "none";
      document.getElementById("start").style.display = "inline-block";

      alert("Could not acquire media: " + err);
    }
  );

  console.log("Call started", new Date().getTime() - startTime);
  document.getElementById("stop").style.display = "inline-block";
}

function stop() {
  stopped = true;
  document.getElementById("stop").style.display = "none";
  document.getElementById("start").style.display = "inline-block";
  document.getElementById("loading").style.display = "block";

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
    document.getElementById("loading").style.display = "none";
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



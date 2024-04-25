import logging
import traceback

import uuid
from fastapi import APIRouter, Request
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCDataChannel
from aiortc.contrib.media import MediaRelay
from sqlalchemy.orm import Session
from ..domain.user import service, schemas, models
from ..dependencies import create_access_token
router = APIRouter(tags=["webrtc_fr"])


class VideoTransformTrack(MediaStreamTrack):
    """
    A video stream track that transforms frames from an another track.
    """

    kind = "video"

    def __init__(self, track, transform, db, request, pc):
        super().__init__()  # don't forget this!
        self.track: MediaStreamTrack = track
        self.pc: RTCPeerConnection = pc
        self.transform: str = transform
        self.db: Session = db
        self.request: Request = request
        self.dc: RTCDataChannel = None
        self.frame_count = 0
        self.face_count = 0
        self.error_count = 0

    def send_message(self, message: str):
        if self.dc is not None and self.dc.readyState == "open":
            self.dc.send(message)
            if self.dc is None:
                self.dc = self.pc.createDataChannel("events")
        else:
            logging.warning("Data channel not open")

    async def send_stop(self, message: str):
        self.send_message("stop")
        self.send_message(message)
        self.dc.close()
        self.track.stop()
        await self.pc.close()

    async def recv(self):
        if self.dc is None:
            self.dc = self.pc.createDataChannel("events")
        else:
            self.send_message("event: frame received")

        frame = await self.track.recv()
        self.frame_count += 1
        if self.transform == "face_recognition":
            if self.frame_count % 10 == 0:
                try:
                    user: models.User = await service.get_user_by_face(self.db, frame)
                    if self.error_count > 0:
                        self.error_count -= 1
                    logging.warning(f"User found: {user.name}")
                    if self.request.state.user_id == user.id:
                        self.face_count += 1
                    else:
                        self.face_count = 0
                    self.request.state.user_id = user.id
                    self.request.state.user_name = user.name

                    print(user)
                    logging.warning(f"User found: {user.name}")
                    if self.face_count > 10:
                        self.send_message("identified")
                        self.send_message("token:" + create_access_token(user))
                        self.send_message(
                            "user:" + self.request.state.user_name)
                except Exception as e:

                    logging.error(f"User recognition exception: {e}")
                    traceback.print_tb(e.__traceback__)
                    self.error_count += 1
                    if self.error_count > 10:
                        logging.error(">>>>>>>>>>>>>>>>>>>>>>>>>> User recognition error <<<<<<<<<<<<<<<<<<<<<<<<")
                        await self.send_stop("error:User recognition error: "+str(e))

            self.send_message("event: frame processed"+str(self.frame_count))
            self.send_message("event: time_base"+str(frame.time_base))
            return frame
        elif self.transform == "face_addition":
            try:
                logging.warning(f"face_addition User ID: {self.request.state.user_id}")
                if self.request.state.user_id is None:
                    await self.send_stop("error:User not authenticated")
                    logging.warning("User not authenticated")
                else:
                    if self.frame_count % 10 == 0:
                        await service.add_user_face(self.db, frame, user_id=self.request.state.user_id)
                        self.face_count += 1
                    if self.face_count > 10:
                        await self.send_stop("User face addedd")
            except Exception as e:
                logging.error(f"adding failed: {e}")
                traceback.print_tb(e.__traceback__)
                await self.send_stop("error:failed to add face: "+str(e))

            self.send_message("event: frame processed"+str(self.frame_count))
            self.send_message("event: time_base"+str(frame.time_base))
            return frame
        else:
            return frame


@router.post("/offer-fr/", response_model=dict)
async def offer(offer_request: schemas.FaceWebRtcOffer, request: Request):
    if request.state._state.get("user_id") is not None:
        logging.warning(f"User ID in offer-fr: {request.state.user_id}")
    else:
        request.state.user_id = None
    app = request.app
    pcs: set = app.pcs
    relay: MediaRelay = app.relay
    db: Session = request.state.db
    request.state.user_name = "unknown"
    offer = RTCSessionDescription(
        sdp=offer_request.sdp, type=offer_request.type)

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pcs.add(pc)

    def log_info(msg, *args):
        logging.warning(pc_id + " " + msg, *args)

    log_info("Created for %s", request.client.host)

    @pc.on("datachannel")
    def on_datachannel(channel: RTCDataChannel):
        logging.warning("Data channel created")

        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                logging.warning("ping received")
                channel.send("pong" + message[4:])
                logging.warning("pong sent")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        log_info("Track %s received", track.kind)

        # if track.kind == "audio":
        # pc.addTrack(player.audio)
        if track.kind == "video":
            pc.addTrack(
                VideoTransformTrack(
                    relay.subscribe(track), pc=pc, db=db, request=request, transform=offer_request.action
                )
            )

        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)

    # handle offer
    await pc.setRemoteDescription(offer)

    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}

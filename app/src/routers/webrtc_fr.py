import asyncio
import cv2
import logging

import uuid
from av import VideoFrame
from fastapi import APIRouter, Request, HTTPException, Response
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCDataChannel
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRelay
from sqlalchemy.orm import Session
from ..domain.user import service, schemas, models
from ..dependencies import create_access_token
router = APIRouter(tags=["webrtc_fr"])


class VideoTransformTrack(MediaStreamTrack):
    """
    A video stream track that transforms frames from an another track.
    """

    kind = "video"

    def __init__(self, track, transform, db, request):
        super().__init__()  # don't forget this!
        self.track: MediaStreamTrack = track
        self.transform: str = transform
        self.db: Session = db
        self.request: Request = request

    async def recv(self):
        frame = await self.track.recv()
        if self.transform == "face_recognition":
            # perform face detection
            if self.request.state:
                print(self.request.state)
            try:
                user: models.User = await service.get_user_by_face(self.db, frame)
                logging.warning(f"User found: {user.name}")
                self.request.state.user_id = user.id
                self.request.state.token = create_access_token(user)
                self.request.state.identified = True
                print(user)
                logging.warning(f"User found: {user.name}")
                img = frame.to_ndarray(format="bgr24")
                cv2.putText(
                    img,
                    user.name,
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
            except Exception as e:
                logging.error(e)
                logging.warning(f"User not found: {e}")
                img = frame.to_ndarray(format="bgr24")
                cv2.putText(
                    img,
                    "Unknown/Face not found",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

            # rebuild a VideoFrame, preserving timing information
            new_frame = VideoFrame.from_ndarray(img, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            return new_frame
        elif self.transform == "face_addition":
            try:
                logging.warning(f"User ID: {self.request.state.user_id}")
                if self.request.state.user_id is None:
                    self.request.state.stop_stream = True
                    self.request.state.stop_reson = "User not authenticated"
                    logging.warning("User not authenticated")
                    img = frame.to_ndarray(format="bgr24")
                    cv2.putText(
                        img,
                        "User not authenticated",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        2,
                        cv2.LINE_AA,
                    )
                await service.add_user_face(self.db, frame, user_id=self.request.state.user_id)
            except Exception as e:
                logging.warning(f"User not found: {e}")
                img = frame.to_ndarray(format="bgr24")
                cv2.putText(
                    img,
                    "failed to add face",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

            # rebuild a VideoFrame, preserving timing information
            new_frame = VideoFrame.from_ndarray(img, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            return new_frame
        else:
            return frame


@router.post("/offer-fr/", response_model=dict)
async def offer(offer_request: schemas.FaceWebRtcOffer, request: Request):
    app = request.app
    pcs: set = app.pcs
    relay: MediaRelay = app.relay
    db: Session = request.state.db

    offer = RTCSessionDescription(
        sdp=offer_request.sdp, type=offer_request.type)

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pcs.add(pc)

    def log_info(msg, *args):
        logging.warning(pc_id + " " + msg, *args)

    log_info("Created for %s", request.client.host)

    @pc.on("datachannel")
    def on_datachannel(channel:RTCDataChannel):
        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])
        send_identified(channel)        
    async def send_identified(channel:RTCDataChannel):            
        while channel.readyState == "open":
            await asyncio.sleep(1)
            if request.state.identified:
                channel.send("identified")
                channel.send("token:" + request.state.token)
    async def send_error(channel:RTCDataChannel):            
        while channel.readyState == "open":
            await asyncio.sleep(1)
            if request.state.stop_stream:
                channel.send("error:" + request.state.stop_reson)
                channel.send("stop")
                await pc.close()
                pcs.discard(pc)
                

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
                    relay.subscribe(track), db=db,request=request, transform=offer_request.action
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

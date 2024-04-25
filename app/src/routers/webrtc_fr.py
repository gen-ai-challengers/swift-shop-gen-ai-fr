import asyncio
import cv2
import logging
import random
import traceback

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

    def __init__(self, track, transform, db, request, pc):
        super().__init__()  # don't forget this!
        self.track: MediaStreamTrack = track
        self.pc:RTCPeerConnection = pc
        self.transform: str = transform
        self.db: Session = db
        self.request: Request = request
        self.dc: RTCDataChannel = None
        self.frame_count = 0
        self.face_count = 0
        self.error_count = 0
        

    async def recv(self):
        if self.dc is None:
            self.dc = self.pc.createDataChannel("events")
            self.dc.send("event: datachannel created")
        else:
            self.dc.send("event: frame recived")


        frame = await self.track.recv()
        self.frame_count += 1
        if self.transform == "face_recognition":
            if self.frame_count % 10 == 0:    
                try:
                    user: models.User = await service.get_user_by_face(self.db, frame)
                    if self.error_count >0:
                        self.error_count -= 1                   
                    logging.warning(f"User found: {user.name}")
                    if self.request.state.user_id == user.id:
                        self.face_count+=1
                    else:
                        self.face_count = 0
                    self.request.state.user_id = user.id
                    self.request.state.user_name = user.name
                    
                    print(user)
                    logging.warning(f"User found: {user.name}")
                    if self.face_count > 10:
                        self.dc.send("identified")
                        self.dc.send("token:" + create_access_token(user))
                        self.dc.send("user:" + self.request.state.user_name)
                except Exception as e:
                    
                    logging.error(f"User recognition exception: {e}")
                    traceback.print_tb(e.__traceback__)
                    self.error_count += 1
                    if self.error_count > 10:
                        self.dc.send("stop")
                        self.dc.send("error:User recognition error: "+str(e))
                        self.dc.close()
                        self.track.stop()
                        await self.pc.close()

            img = frame.to_ndarray(format="bgr24")
            cv2.putText(
                    img,
                    self.request.state.user_name,
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
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
                logging.warning(f"face_addition User ID: {self.request.state.user_id}")
                if self.request.state.user_id is None:
                    self.dc.send("stop")
                    self.dc.send("User not authenticated")
                    self.dc.close()
                    self.track.stop()
                    await self.pc.close()  
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
                else:
                    if self.frame_count % 10 == 0:    
                        await service.add_user_face(self.db, frame, user_id=self.request.state.user_id)
                        self.face_count += 1
                    if self.face_count > 10:
                        self.dc.send("stop")
                        self.dc.send("User face addedd")
                        self.dc.close()
                        self.track.stop()
                        await self.pc.close()  
                    img = frame.to_ndarray(format="bgr24")
                    cv2.putText(
                        img,
                        "User face added",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        2,
                        cv2.LINE_AA,
                    )
            except Exception as e:
                logging.error(f"adding failed: {e}")
                traceback.print_tb(e.__traceback__)
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
                self.dc.send("stop")
                self.dc.send("error:failed to add face: "+str(e))
                self.dc.close()
                self.track.stop()
                await self.pc.close()


            # rebuild a VideoFrame, preserving timing information
            new_frame = VideoFrame.from_ndarray(img, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            return new_frame
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
    def on_datachannel(channel:RTCDataChannel):
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
                    relay.subscribe(track),pc=pc, db=db,request=request, transform=offer_request.action
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

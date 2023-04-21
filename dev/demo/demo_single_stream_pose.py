from pyxy3d.trackers.pose_tracker import PoseTracker
from queue import Queue
from pyxy3d.cameras.camera import Camera
from pyxy3d.cameras.live_stream import LiveStream
import cv2

ports = [0]
# ports = [3]

cams = []
for port in ports:
    print(f"Creating camera {port}")
    cam = Camera(port)
    cam.exposure = -7
    cams.append(cam)

# standard inverted charuco
# charuco = Charuco(
#     4, 5, 11, 8.5, aruco_scale=0.75, square_size_overide_cm=5.25, inverted=True
# )
tracker = PoseTracker()

frame_packet_queues = {}


streams = []
for cam in cams:

    q = Queue(-1)
    frame_packet_queues[cam.port] = q

    print(f"Creating Video Stream for camera {cam.port}")
    stream = LiveStream(cam, fps_target=5, tracker=tracker)
    stream.subscribe(frame_packet_queues[cam.port])
    stream._show_fps = True
    stream.show_points(True)
    streams.append(stream)

while True:
    try:
        for port in ports:
            frame_packet = frame_packet_queues[port].get()

            cv2.imshow(
                (str(port) + ": 'q' to quit and attempt calibration"),
                frame_packet.frame_with_points,
            )

    # bad reads until connection to src established
    except AttributeError:
        pass

    key = cv2.waitKey(1)

    if key == ord("q"):
        for stream in streams:
            stream.camera.capture.release()
        cv2.destroyAllWindows()
        exit(0)

    if key == ord("v"):
        for stream in streams:
            print(f"Attempting to change resolution at port {stream.port}")
            stream.change_resolution((640,480))

    if key == ord("s"):
        for stream in streams:
            stream.stop()
        cv2.destroyAllWindows()
        exit(0)

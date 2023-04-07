
import pyxy3d.logger

logger = pyxy3d.logger.get(__name__)

from time import sleep
import shutil
from pathlib import Path
from pyxy3d.cameras.camera_array import CameraArray
from pyxy3d import __root__
from pyxy3d.calibration.capture_volume.capture_volume import CaptureVolume
from pyxy3d.cameras.camera_array_initializer import CameraArrayInitializer
from pyxy3d.calibration.capture_volume.point_estimates import PointEstimates 
from pyxy3d.calibration.capture_volume.helper_functions.get_point_estimates import get_point_estimates
import pytest
from pyxy3d.calibration.charuco import Charuco, get_charuco
from pyxy3d.calibration.corner_tracker import CornerTracker
from pyxy3d.calibration.monocalibrator import MonoCalibrator
from pyxy3d.cameras.camera import Camera
from pyxy3d.cameras.synchronizer import Synchronizer
from pyxy3d.cameras.camera_array_initializer import CameraArrayInitializer


from pyxy3d.calibration.stereocalibrator import StereoCalibrator
from pyxy3d.calibration.capture_volume.point_estimates import PointEstimates
from pyxy3d.calibration.capture_volume.capture_volume import CaptureVolume
from pyxy3d.calibration.capture_volume.quality_controller import QualityController

from pyxy3d.cameras.camera_array import CameraArray, CameraData
from pyxy3d.calibration.capture_volume.helper_functions.get_point_estimates import (
    get_point_estimates,
)

from pyxy3d.cameras.live_stream import LiveStream
from pyxy3d.recording.video_recorder import VideoRecorder
from pyxy3d.recording.recorded_stream import RecordedStream, RecordedStreamPool

from pyxy3d.session import FILTERED_FRACTION

TEST_SESSIONS = ["217"]


def copy_contents(src_folder, dst_folder):
    """
    Helper function to port a test case data folder over to a temp directory 
    used for testing purposes so that the test case data doesn't get overwritten
    """
    src_path = Path(src_folder)
    dst_path = Path(dst_folder)

    # Create the destination folder if it doesn't exist
    dst_path.mkdir(parents=True, exist_ok=True)

    for item in src_path.iterdir():
        # Construct the source and destination paths
        src_item = src_path / item
        dst_item = dst_path / item.name

        logger.info(f"Copying {src_item} to {dst_item}")

        # Copy file or directory
        if src_item.is_file():
            logger.info("Copying over file")
            shutil.copy2(src_item, dst_item)  # Copy file preserving metadata
            # while src_item.stat().st_size != dst_item.stat().st_size:
                # logger.info(f"Waiting for {dst_item} to finish copying") 

        # elif src_item.is_dir():
            # logger.info("Copying over directory")
            # shutil.copytree(src_item, dst_item)


@pytest.fixture(params=TEST_SESSIONS)
def session_path(request, tmp_path):
    """
    Tests will be run based on data stored in tests/sessions, but to avoid overwriting
    or altering test cases,the tested directory will get copied over to a temp
    directory and then that temp directory will be passed on to the calling functions
    """
    original_test_data_path = Path(__root__, "tests", "sessions", request.param)
    tmp_test_data_path = Path(tmp_path,request.param)
    copy_contents(original_test_data_path,tmp_test_data_path)    
    
    # return tmp_test_data_path
    return original_test_data_path


    
# def test_capture_volume_optimization(session_path):
#     """
#     requires as a baseline a stereocalibrated config.toml file
#     """    
#     config_path = Path(session_path, "config.toml")
#     initializer = CameraArrayInitializer(config_path)
#     camera_array = initializer.get_best_camera_array()
#     point_data_path = Path(session_path, "point_data.csv")
#     point_estimates: PointEstimates = get_point_estimates(camera_array, point_data_path)
#     capture_volume = CaptureVolume(camera_array, point_estimates)
#     initial_rmse = capture_volume.rmse
#     capture_volume.optimize()
#     optimized_rmse = capture_volume.rmse

#     # rmse should go down after optimization
#     for key, rmse in initial_rmse.items():
#         assert(rmse>=optimized_rmse[key])

def test_post_monocalibration(session_path):
  
    
   
    # This test begins with a set of cameras with calibrated intrinsics
    config_path = str(Path(session_path, "config.toml"))
    logger.info(f"Getting charuco from config at {config_path}")
    charuco = get_charuco(config_path)
    
    # need to create point_data    
    # this is where it will be stored by VideoRecorder
    point_data_path = Path(session_path, "point_data.csv")

    # play back pre-recorded videos
    # get the ports of the videos to create the streampool
    ports = []
    for item in session_path.iterdir():
        if item.name.split(".")[1] == "mp4":
            port = item.stem.split("_")[1]
            port = int(port)
            ports.append(port)
    logger.info(f"Identifying ports to process: {ports}")
 
    # create a synchronizer based off of these stream pools 
    logger.info(f"Creating RecordedStreamPool")
    stream_pool = RecordedStreamPool(session_path, charuco=charuco)
    logger.info("Creating Synchronizer")
    syncr = Synchronizer(stream_pool.streams, fps_target=3)

    # video recorder needed to save out points.csv.
    logger.info(f"Creating test video recorder to save out point data")
    video_recorder = VideoRecorder(syncr)
    video_recorder.start_recording(session_path, include_video=False)

    logger.info("Initiate playing stream pool videos...")
    stream_pool.play_videos()

    # need to wait for points.csv file to populate
    while not point_data_path.exists():
        logger.info("Waiting for point_data.csv to populate...")
        sleep(1)
    
    logger.info(f"Waiting for video recorder to finish processing stream...")
    stereocalibrator = StereoCalibrator(config_path, point_data_path)
    stereocalibrator.stereo_calibrate_all(boards_sampled=10)

    camera_array: CameraArray = CameraArrayInitializer(
        config_path
    ).get_best_camera_array()

    point_estimates: PointEstimates = get_point_estimates(
        camera_array, point_data_path
    )

    capture_volume = CaptureVolume(camera_array, point_estimates)
    initial_rmse = capture_volume.rmse
    logger.info(f"Prior to bundle adjustment, RMSE error is {initial_rmse}")
    capture_volume.optimize()

    quality_controller = QualityController(capture_volume, charuco)
    # Removing the worst fitting {FILTERED_FRACTION*100} percent of points from the model
    logger.info(f"Filtering out worse fitting {FILTERED_FRACTION*100} % of points")
    quality_controller.filter_point_estimates(FILTERED_FRACTION)
    logger.info("Re-optimizing with filtered data set")
    capture_volume.optimize()
    optimized_filtered_rmse = capture_volume.rmse

if __name__ == "__main__":
    
    original_session_path = Path(__root__, "tests", "sessions", "217")    
    session_path = Path(original_session_path.parent.parent,"sessions_copy_delete","217")
    copy_contents(original_session_path,session_path)

    test_post_monocalibration(session_path)
    
    
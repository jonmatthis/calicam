
import pyxy3d.logger

logger = pyxy3d.logger.get(__name__)

import os
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

        # Copy file or directory
        if src_item.is_file():
            shutil.copy2(src_item, dst_item)  # Copy file preserving metadata
        elif src_item.is_dir():
            shutil.copytree(src_item, dst_item)


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
    charuco = get_charuco(config_path)
    
    # need to create point_data    
    # this is where it will be stored by VideoRecorder
    point_data_path = Path(session_path, "point_data.csv")

    # play back pre-recorded videos

    # get the por
    ports = []
    for item in session_path.iterdir():
        if item.name.split(".")[1] == "mp4":
            port = item.stem.split("_")[1]
            port = int(port)
            ports.append(port)
  
    stream_pool = RecordedStreamPool(ports, recording_directory, charuco=charuco)
    logger.info("Creating Synchronizer")
    syncr = Synchronizer(stream_pool.streams, fps_target=3)
    stream_pool.play_videos()


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
    capture_volume.optimize()

    quality_controller = QualityController(capture_volume, charuco)
    quality_controller.filter_point_estimates(FILTERED_FRACTION)

    optimized_filtered_rmse = capture_volume.rmse
    # Removing the worst fitting {FILTERED_FRACTION*100} percent of points from the model

if __name__ == "__main__":
    
    session_path = Path(__root__, "tests", "sessions", "217")    
    test_post_monocalibration(session_path)
    
    
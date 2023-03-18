# %%
 
from pathlib import Path
from pyxy3d.cameras.camera_array_builder import CameraArrayBuilder    
from pyxy3d.cameras.camera_array import CameraData

from pyxy3d import __root__
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import toml
 
@dataclass
class StereoPair:
    """
    A dataclass to hold the extrinsic parameters associated with the cv2.stereoCalibrate
    function output. Additionally provides some convenience methods to get common transformations
    of the data.
    
    From the first output of cv2.stereocalibrate, variations can be created by inverting camera
    relationships, and chaining together relative camera positions so that all possible pairs
    of cameras are represented. This dataclass is the building block of that larger process.
    """
    primary_port: int
    secondary_port: int
    error_score: float # when chaining operations, this will be a cumulative number
    translation: np.ndarray
    rotation: np.ndarray
    
    @property
    def pair(self):
        return (self.primary_port,self.secondary_port)

    @property
    def transformation(self):
    
        R_stack = np.vstack([self.rotation, np.array([0,0,0])])
        t_stack = np.vstack([self.translation, np.array([1])])
        Tranformation = np.hstack([R_stack,t_stack])
        return Tranformation


def get_inverted_stereopair(stereo_pair:StereoPair)->StereoPair:
    primary_port = stereo_pair.secondary_port
    secondary_port = stereo_pair.primary_port
    error_score = stereo_pair.error_score

    inverted_transformation = np.linalg.inv(stereo_pair.transformation)
    rotation = inverted_transformation[0:3,0:3]
    translation = inverted_transformation[0:3,3:]
    
    inverted_stereopair = StereoPair(primary_port = primary_port,
                                     secondary_port = secondary_port,
                                     error_score = error_score,
                                     translation = translation,
                                     rotation = rotation)
    return inverted_stereopair

def get_all_stereopairs(config_path:Path)->dict:

    config = toml.load(config_path)
    stereopairs = {}

    # Create StereoPair objects for each saved stereocalibration output in config
    # this are maintained in a dictionary keyed off of the pair tuple
    for key, params in config.items():
        if key.split("_")[0] == "stereo":
            port_A = int(key.split("_")[1])
            port_B = int(key.split("_")[2])

            rotation = np.array(params["rotation"], dtype=np.float64)
            translation = np.array(params["translation"], dtype=np.float64)
            error = float(params["RMSE"])

            new_stereopair = StereoPair(primary_port = port_A,
                                        secondary_port = port_B,
                                        error_score = error,
                                        translation = translation,
                                        rotation = rotation)

            stereopairs[new_stereopair.pair] = new_stereopair

    # create another dictionary that will contain the inverted versions of the StereoPairs
    inverted_stereopairs = {}
    for pair, stereopair in stereopairs.items():
        a,b = pair
        inverted_pair = (b,a)
        inverted_stereopairs[inverted_pair] = get_inverted_stereopair(stereopair)
    
    # combine the dictionaries
    merged_stereopairs = {**stereopairs, **inverted_stereopairs}
    return merged_stereopairs

# def get_anchored_pairs(anchor: int, all_stereopairs:dict)->dict:



if __name__ == "__main__":
    session_directory = Path(__root__,  "tests", "3_cameras_middle")
    config_path = Path(session_directory, "config.toml")

    all_stereopairs = get_all_stereopairs(config_path)
    # drafting code to get the array in terms of 
    config = toml.load(config_path)

    anchor = 1 
    cameras = {}

    for key, data in config.items():
        if key.startswith("cam_") and not config[key]['ignore']:
            port = data["port"]
            size = data["size"]
            rotation_count = data["rotation_count"]
            error = data["error"]
            matrix = np.array(data["matrix"], dtype=np.float64)
            distortions = np.array(data["distortions"], dtype=np.float64)
            exposure = data["exposure"]
            grid_count = data["grid_count"]
            ignore = data["ignore"]
            verified_resolutions = data["verified_resolutions"]

            # update with extrinsics, though place anchor camera at origin
            if port == anchor:
                translation = np.array([0, 0, 0], dtype=np.float64)
                rotation = np.array(
                    [[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64
                )
            else:
                anchored_stereopair = all_stereopairs[(anchor,port)]
                translation = anchored_stereopair.translation
                rotation = anchored_stereopair.rotation


            cam_data = CameraData(
                port,
                size,
                rotation_count,
                error,
                matrix,
                distortions,
                exposure,
                grid_count,
                ignore,
                verified_resolutions,
                translation,
                rotation,
            )

            cameras[port] = cam_data
    
    
    camera_A = cameras[0]
            
    rot_A = np.linalg.inv(camera_A.rotation)
    trans_A = np.array(camera_A.translation) * -1
    rot_trans_A = np.column_stack([rot_A, trans_A])
    mtx_A = camera_A.matrix
    proj_A = mtx_A @ rot_trans_A   
    
    rot_A_alt = camera_A.rotation
    trans_A_alt = camera_A.translation 
    rot_trans_A = np.column_stack([rot_A_alt, trans_A_alt])
    mtx_A = camera_A.matrix
    proj_A_alt = mtx_A @ rot_trans_A   
    
#%%
# this is an awesome two-liner to convert a dictionary of dataclasses to a pandas dataframe
# stereopair_dict = {k:asdict(merged_stereopairs) for k,merged_stereopairs in merged_stereopairs.items()}
# df = pd.DataFrame(list(stereopair_dict.values()), index=stereopair_dict.keys())


# %%

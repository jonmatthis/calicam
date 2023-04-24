

#%%

from pyxy3d.triangulate.helper import create_labelled_csv
from pyxy3d.trackers.holistic_tracker import HolisticTracker, HolisticTrackerFactory
from pathlib import Path
from pyxy3d import __root__
import pandas as pd

recording_path = Path(__root__,"dev", "sample_sessions", "test_calibration", "recording_1")
xyz_csv_path = Path(recording_path, "xyz.csv")
tracker = HolisticTracker()

# read in xyz path as pandas dataframe
# wishing now that I had started out with polars, but here we are... 
df_xyz = pd.read_csv(xyz_csv_path)
df_xyz.drop("Unnamed: 0", axis=1)

df_xyz = df_xyz.rename({"x_coord":"x",
                        "y_coord":"y",
                        "z_coord":"z",               
                        }, axis=1)
df_xyz = df_xyz[["sync_index", "point_id", "x", "y", "z"]]
df_xyz["point_name"] = df_xyz["point_id"].map(tracker.get_point_name)
# pivot the DataFrame wider
df_wide = df_xyz.pivot_table(
    index=['sync_index'],
    columns='point_name',
    values=['x', 'y', 'z']
)

# flatten the column names
df_wide.columns = ['{}_{}'.format(y,x) for x, y in df_wide.columns]
# reset the index
df_wide = df_wide.reset_index()
# merge the rows with the same sync_index
df_merged = df_wide.groupby('sync_index').agg('first')

# sort the dataframe
#%%
df_merged = df_merged.sort_index(axis=1,ascending=True)
df_merged.to_csv(Path(xyz_csv_path.parent, "tabular_xyz.csv"))
# pivot dataframe
# %%

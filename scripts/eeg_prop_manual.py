# This script is for calculating the properties of the EEG data, such as the sampling rate,
# number of channels, and duration of the recording.

import mne
import pandas as pd
from pathlib import Path
mne.set_config("MNE_BROWSER_USE_OPENGL",'true') # Enable OpenGL for better performance when plotting large datasets
mne.set_config("MNE_BROWSER_THEME",'light')


root_path = Path('../')
data_path = root_path / 'datas'
res_path = root_path / 'result'
info_data = pd.read_excel(data_path / 'ele_pos.xlsx')

info_data['patient_id'] = info_data['patient_id'].astype(str)
patients_list = info_data['patient_id'].unique().tolist()

raw_file_path = list((data_path / "data_00_rawECoG").glob('*_929304_*.edf'))[0]

raw = mne.io.read_raw_edf(raw_file_path, preload=True)

#%%
raw_file_path = Path(r"H:\lyz\Ecog-glioma\datas\data_00_rawECoG\20251020_936377_1.edf")
raw = mne.io.read_raw_edf(raw_file_path, preload=True)
raw.filter(1, 150)
raw.plot(n_channels=len(raw.ch_names))

time_start = 20
raw_cut = raw.copy().crop(tmin=time_start, tmax=time_start+120)
raw_cut.plot()

raw_cut.save(data_path/ "data_01_ECoG_clean_1" / (raw_file_path.stem + ".fif") , overwrite=False)
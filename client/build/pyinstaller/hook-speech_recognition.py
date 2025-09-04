# PyInstaller hook for speech_recognition
# This hook excludes the problematic x86_64 flac-mac binary

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Exclude the problematic flac-mac binary
excludedimports = ['speech_recognition.flac-mac']

# Collect data files but exclude flac-mac
datas = collect_data_files('speech_recognition')
datas = [item for item in datas if 'flac-mac' not in item[0]]

# Collect submodules
hiddenimports = collect_submodules('speech_recognition')

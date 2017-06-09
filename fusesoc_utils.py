import os

from fusesoc.coremanager import CoreManager
from fusesoc import vlnv

cm = CoreManager()


def get_filenames_from_core(top_core_name):
    top_core = vlnv.Vlnv(top_core_name)
    cores = cm.get_depends(top_core)
    filenames = []
    usage = ['sim']
    for core in cores:
        core.setup()
        basepath = core.files_root
        for fs in core.file_sets:
            usage_matches = set(fs.usage) & set(usage)
            if usage_matches and ((core.name.name == top_core.name) or not fs.private):
                filenames += [os.path.join(basepath, f.name) for f in fs.file
                              if f.name[-3:] != '.py']
    return filenames

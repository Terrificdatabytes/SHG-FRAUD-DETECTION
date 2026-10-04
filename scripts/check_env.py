#!/usr/bin/env python
import platform,sys,os,shutil,time,importlib
print('Architecture:',platform.machine()); print('OS:',platform.platform()); print('Python:',sys.version.split()[0]); print('CPU count:',os.cpu_count()); print('Free disk GB:',round(shutil.disk_usage('.').free/1e9,1))
mods=['numpy','pandas','scipy','sklearn','networkx','torch','streamlit','plotly','pyvis','gudhi']
for m in mods:
 try: x=importlib.import_module(m); print(f'{m}: {getattr(x,"__version__","OK")}')
 except Exception as e: print(f'{m}: MISSING ({e})')
import torch
t=time.perf_counter(); a=torch.rand(700,700); _=a@a; print('Torch CPU:',not torch.cuda.is_available(),'threads:',torch.get_num_threads(),'matmul ms:',round((time.perf_counter()-t)*1000))

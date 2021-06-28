from tkinter import Label
import matplotlib.pyplot as plt
import matplotlib.ticker as tckr
import json
import sys
import numpy as np

stepNr = []  
numTHP = []
numPages = []
totAlloc = []
totVAlloc = [] 
totTHPAlloc = []    
elapsedTime = [] 

print(sys.argv[1])
with open("stored_data/{}".format(sys.argv[1])) as file:
    data = json.load(file)
    for step, values in data.items():
        stepNr.append(step)
        numTHP.append(values["THP"])
        numPages.append(values["Pages"])
        totAlloc.append(values["TotAlloc"])
        totVAlloc.append(values["TotVAlloc"])
        totTHPAlloc.append(values["THPAlloc"])
        elapsedTime.append(values["Time"])

file.close()

xAxis = np.arange(0, len(stepNr), 1)
fig1, (ax11,ax21) = plt.subplots(2,1, figsize=(7,8))

ax12 = ax11.twinx()
ax11.plot(xAxis, numTHP, color='tab:blue', label='Nr THP')
ax11.set_xlabel("Update Nr")
ax11.set_ylabel("Nr THP")
ax12.plot(xAxis, numPages, color='tab:red', label='Nr Pages')
ax12.set_ylabel("Nr Pages")

ax11.tick_params(axis='y')
ax11handle, ax11label = ax11.get_legend_handles_labels()
ax12handle, ax12label = ax12.get_legend_handles_labels()

ax11.legend(ax11handle+ax12handle, ax11label+ax12label,loc='center', ncol=2, bbox_to_anchor=(0.5, 1.1))
ax11.set_xlim([0, int(stepNr[-1])+1])

ax21.set_xlim([0, int(stepNr[-1])+1])

# ax22.set_xlim([0, int(stepNr[-1])+1])
ax21.plot(xAxis, totAlloc, color='tab:green', label='Physical')
ax21.plot(xAxis, totVAlloc, color='tab:red', label='Virtual')
ax21.set_xlabel("Update Nr")
ax21.set(ylabel="Physical, Virtual & THP Allocation [MB]")
ax21.plot(xAxis, totTHPAlloc, color='tab:blue', label='THP')

ax22 = ax21.twinx()
ax22.plot(xAxis, elapsedTime, color='tab:cyan', linestyle=':', label='Update time')
# ax22.set_ylim(0, max(elapsedTime)*1.5)
ax22.set(ylabel="Time between Updates [s]") 


ax21handle, ax21label = ax21.get_legend_handles_labels()
ax22handle, ax22label = ax22.get_legend_handles_labels()
# ax21.legend(ax21handle+ax22handle+ax23handle, ax21label+ax22label+ax23label,loc='center', ncol=3, bbox_to_anchor=(0.65, 1.1))
ax21.legend(ax21handle+ax22handle, ax21label+ax22label,loc='center', ncol=2, bbox_to_anchor=(0.50, 1.1))

fig1.tight_layout(pad=3)
fig1.suptitle("{}".format(sys.argv[1]))
plt.savefig("pageViz_graphs/{}.svg".format(sys.argv[1]))
plt.show()
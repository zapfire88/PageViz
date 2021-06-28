import subprocess as sp
import os
import sys
import struct
import tkinter as tk
from tkinter import messagebox
import time
import json
import psutil as psu
from pytictoc import TicToc


if len(sys.argv) < 2:
    print("Wrong Input: {}".format(str(sys.argv)))
    print("sudo python3 pageViz.py programToCheck args")
    sys.exit(1)

cwd = os.getcwd()
global pid
global pagemapPath

pageSize = os.sysconf("SC_PAGE_SIZE")
hugePageSize = pageSize*512
pageFlagPath = "/proc/kpageflags"
global step
global data
data = {} 
step = 0
numTHP = 0
numPages = 0
totAllocMem = 0
totVAllocMem = 0
maxCol = 113
global t
t = TicToc()

#--------------------------------------------------------------------------------------------------------------------#

def cmdLine (command: str):
    output = sp.check_output(command, shell=True)
    return output
#--------------------------------------------------------------------------------------------------------------------#

def updateTotAllocMem():
    tempText = str(cmdLine("ps u -p {0} | awk '{{print $6}}'".format(pid)))
    tempText = tempText.replace("b'RSS\\n", '')
    tempText = tempText.replace("'", '')
    tempText = tempText.replace('\\n', '').strip()
    return int(tempText)


#--------------------------------------------------------------------------------------------------------------------#

def updateTotVAllocMem():
    tempText = str(cmdLine("ps u -p {0} | awk '{{print $5}}'".format(pid)))
    tempText = tempText.replace("b'VSZ\\n", '')
    tempText = tempText.replace("'", '')
    tempText = tempText.replace('\\n', '').strip()
    return int(tempText)
#--------------------------------------------------------------------------------------------------------------------#

def getVaddress():
    temp = str(cmdLine("cat /proc/{0}/maps | awk '{{print $1}}'".format(pid)))
    temp = temp.replace('\\n', ' ')
    temp = temp.replace('-', ' ').split()
    temp[0] = temp[0][2:]
    pairVaddList = []
    for i in range(0, len(temp[:-1]), 2):
        pairVaddList.append([temp[i],temp[i+1]]) 
    return pairVaddList[:-1]

#--------------------------------------------------------------------------------------------------------------------#

# Creating main window
mainWindow = tk.Tk()
mainWindow.title("PageViz")
mainWindow.geometry('1280x720')
mainWindow.resizable(width=False, height=True)

# Adding labels to both canvases
VaddLabel = tk.Label(mainWindow, text='V-Addresses')
VaddLabel.place(relx = 0.008, rely=0.02, anchor='nw')
cellLabel = tk.Label(mainWindow, text='Cells (Pages/THP)')
cellLabel.place(relx = 0.5, rely=0.02, anchor='nw')

# Adding canvas containing labels
winBotCanvas = tk.Canvas(mainWindow, height=40, highlightbackground='grey', highlightthickness=2)
winBotCanvas.pack(side=tk.BOTTOM, fill='x', padx=(10,23), pady=10)
winBotCanvas.create_rectangle(20,8,30,18, outline='grey', fill='yellow', width=2)
winBotCanvas.create_text(35,13, text="THP (2MB/cell)", anchor=tk.W)
winBotCanvas.create_rectangle(20,25,30,35, outline='grey', fill='lightgreen', width=2)
winBotCanvas.create_text(35,30, text="Present", anchor=tk.W)
winBotCanvas.create_rectangle(200,8,210,18, outline='grey', fill='blue', width=2)
winBotCanvas.create_text(215,13, text="Swapped", anchor=tk.W)
winBotCanvas.create_rectangle(200,25,210,35, outline='grey', fill='lightgrey', width=2)
winBotCanvas.create_text(215,30, text="Not in memory", anchor=tk.W)
tNumTHP = winBotCanvas.create_text(340,12, text="Nr of THP(2MB): {}".format(numTHP), anchor=tk.W)
tNumPage = winBotCanvas.create_text(340,32, text="Nr of Pages(4kB): {}".format(numPages), anchor=tk.W)
tAllMem = winBotCanvas.create_text(550, 12, text="Total allocated memory: {:.2f}MB".format(totAllocMem), anchor=tk.W)
tAllTHP = winBotCanvas.create_text(550, 32, text="Total allocated THP: {:.2f}MB".format(numTHP*2.0), anchor=tk.W)
tAllVMem = winBotCanvas.create_text(840, 12, text="Total allocated V-memory: {:.2f}MB".format(totVAllocMem), anchor=tk.W)
updSincStart = winBotCanvas.create_text(840, 32, text="Updates since start: {}".format(step), anchor=tk.W)
# Adding canvas containing virtual Adresses
winLeftCanvas = tk.Canvas(mainWindow, width=80, highlightbackground='grey', highlightthickness=2)
winLeftCanvas.pack(side=tk.LEFT, fill='y', padx=(10,10), pady=(40,0))

# Adding canvas containing all cells corresponding to each page entry
winCanvas = tk.Canvas(mainWindow, highlightbackground='grey', highlightthickness=2)
winCanvas.pack(side=tk.LEFT, fill='both', expand=True, padx=(10,1), pady=(40,0))

def multiple_yview(*args):
    winCanvas.yview(*args)
    winLeftCanvas.yview(*args)

# Adding scrollbar to the window
scrollBar = tk.Scrollbar(mainWindow, command=multiple_yview)
scrollBar.pack(side=tk.RIGHT, padx=(0,9), pady=(40,0), fill='y')

# Binding update scrollbar function
winCanvas.configure(yscrollcommand=scrollBar.set)
winLeftCanvas.configure(yscrollcommand=scrollBar.set)


#--------------------------------------------------------------------------------------------------------------------#

def justUpdate(entries, vAdd, row, col): 
    global iterSize
    newNumPages = 0
    newNumTHP = 0
    if psu.pid_exists(pid) == False:
        return
    with open(pagemapPath, 'rb') as frameFile: 
        with open(pageFlagPath, 'rb') as flagFile: 
            i = int(vAdd[0], base=16)
            stopAdd = int(vAdd[1], base=16)
            while i < stopAdd:
                frameOffset = int((i / pageSize) * 8)
                frameFile.seek(frameOffset)
                try:
                    frame = struct.unpack('Q', frameFile.read(8))[0]
                except:
                    break
                
                if i not in entries:

                    if frame == 0:
                        isSwapped = False
                        isPresent = False
                        isTHP = False
                    else:
                        flagOffset = (frame & ((1 << 54)-1)) * 8
                        flagFile.seek(flagOffset) 
                        try:
                            isTHP = (struct.unpack('Q', flagFile.read(8))[0] & (1 << 22)) != 0
                        except:
                            isTHP = False
                        isSwapped = (frame & (1 << 62)) != 0
                        isPresent = (frame & (1 << 63)) != 0
                        if isTHP == True:
                            newNumTHP += 1
                            iterSize = hugePageSize
                        else: 
                            newNumPages += 1
                            iterSize = pageSize
                    entries[i] = {"Frame": frame, "Swap": isSwapped, "Present": isPresent, "THP": isTHP, "Changed": True, "XY": (col, row), "Checked": True}  
                else:
                    if frame == 0:
                        if entries[i]["Frame"] != 0:
                            entries[i]["Frame"] = frame
                            entries[i]["Swap"] = False
                            entries[i]["Present"] = False
                            entries[i]["THP"] = False
                            entries[i]["Changed"] = True  
                        else:
                            entries[i]["Swap"] = False
                            entries[i]["Present"] = False
                            entries[i]["THP"] = False
                    else: 
                        flagOffset = (frame & ((1 << 54)-1)) * 8
                        flagFile.seek(flagOffset) 
                        try:
                            isTHP = (struct.unpack('Q', flagFile.read(8))[0] & (1 << 22)) != 0
                        except:
                            isTHP = False
                        isSwapped = (frame & (1 << 62)) != 0
                        if entries[i]["Swap"] != isSwapped:
                            entries[i]["Swap"] = isSwapped
                            entries[i]["Changed"] = True
                 
                        isPresent = (frame & (1 << 63)) != 0
                        if entries[i]["Present"] != isPresent:
                            entries[i]["Present"] = isPresent
                            entries[i]["Changed"] = True

                        if isTHP == True:
                            newNumTHP += 1
                            iterSize = hugePageSize
                            if entries[i]["THP"] == False:
                                entries[i]["THP"] = isTHP
                                entries[i]["Changed"] = True
                        else: 
                            if entries[i]["THP"] == True:
                                entries[i]["THP"] = isTHP
                                entries[i]["Changed"] = True
                            newNumPages += 1
                            iterSize = pageSize
                    entries[i]["Checked"] = True 
                    entries[i]["XY"] = (col, row) 
                if col >= maxCol:
                    col = 0
                    row += 1
                else:
                    col += 1
                i += iterSize   
    return entries, row, col, newNumPages, newNumTHP

#--------------------------------------------------------------------------------------------------------------------#

def updateStart(entries, vAdd, startAdd, row, col):
    global iterSize
    newNumPages = 0
    newNumTHP = 0
    startVAdd = int(vAdd[0], base=16)
    oldStartAdd = int(startAdd, base=16)
    stopAddress = int(vAdd[1], base=16)
    with open(pagemapPath, 'rb') as frameFile: 
        with open(pageFlagPath, 'rb') as flagFile: 

            i = min(startVAdd, oldStartAdd)
            while i < stopAddress:
                if i < startVAdd and i >= oldStartAdd:
                    if i in entries and "Cell" in entries[i]: 
                        if entries[i]["THP"] == True:
                            print(entries[i]["Checked"])
                            iterSize = hugePageSize
                            newNumTHP -= 1
                        else:
                            iterSize = pageSize
                            newNumPages -= 1
                        newNumPages -= 1
                        i += iterSize
                    continue
                elif i >= startVAdd and i < oldStartAdd:
                    frameOffset = int((i / pageSize) * 8)
                    frameFile.seek(frameOffset)
                    try:
                        frame = struct.unpack('Q', frameFile.read(8))[0]
                    except:
                        break
                    if frame == 0:
                        isSwapped = False
                        isPresent = False
                        isTHP = False
                    else:
                        isSwapped = (frame & (1 << 62)) != 0
                        isPresent = (frame & (1 << 63)) != 0

                        flagOffset = (frame & ((1 << 54)-1)) * 8
                        flagFile.seek(flagOffset) 
                        try:
                            isTHP = (struct.unpack('Q', flagFile.read(8))[0] & (1 << 22)) != 0
                        except:
                            isTHP = False
                        if isTHP == True:
                            newNumTHP += 1
                            iterSize = hugePageSize
                        else: 
                            newNumPages += 1
                            iterSize = pageSize
                    entries[i] = {"Frame": frame, "Swap": isSwapped, "Present": isPresent, "THP": isTHP, "Changed": True, "XY": (col, row), "Checked": True} 
                else:
                    if i not in entries:
                        frameOffset = int((i / pageSize) * 8)
                        frameFile.seek(frameOffset)
                        try:
                            frame = struct.unpack('Q', frameFile.read(8))[0]
                        except:
                            break
                        if frame == 0:
                            isSwapped = False
                            isPresent = False
                            isTHP = False

                        else:
                            isSwapped = (frame & (1 << 62)) != 0
                            isPresent = (frame & (1 << 63)) != 0

                            flagOffset = (frame & ((1 << 54)-1)) * 8
                            flagFile.seek(flagOffset) 
                            try:
                                isTHP = (struct.unpack('Q', flagFile.read(8))[0] & (1 << 22)) != 0
                            except:
                                isTHP = False
                            if isTHP == True:
                                newNumTHP += 1
                                iterSize = hugePageSize
                            else: 
                                newNumPages += 1
                                iterSize = pageSize
                        entries[i] = {"Frame": frame, "Swap": isSwapped, "Present": isPresent, "THP": isTHP, "Changed": True, "XY": (col, row), "Checked": True}
                    else:
                        frameOffset = int((i / pageSize) * 8)
                        frameFile.seek(frameOffset)
                        try:
                            frame = struct.unpack('Q', frameFile.read(8))[0]
                        except:
                            break
                        if frame == 0:
                            if entries[i]["Frame"] != 0:
                                entries[i]["Frame"] = frame
                                entries[i]["Swap"] = False
                                entries[i]["Present"] = False
                                entries[i]["THP"] = False
                                entries[i]["Changed"] = True  
                            else:
                                entries[i]["Swap"] = False
                                entries[i]["Present"] = False
                                entries[i]["THP"] = False 

                        else: 
                            isSwapped = (frame & (1 << 62)) != 0
                            if entries[i]["Swap"] != isSwapped:
                                entries[i]["Swap"] = isSwapped
                                entries[i]["Changed"] = True
                            
                            isPresent = (frame & (1 << 63)) != 0
                            if entries[i]["Present"] != isPresent:
                                entries[i]["Present"] = isPresent
                                entries[i]["Changed"] = True

                            flagOffset = (frame & ((1 << 54)-1)) * 8
                            flagFile.seek(flagOffset) 
                            try:
                                isTHP = (struct.unpack('Q', flagFile.read(8))[0] & (1 << 22)) != 0
                            except:
                                isTHP = False
                            if isTHP == True:
                                newNumTHP += 1
                                iterSize = hugePageSize
                                if entries[i]["THP"] == False:
                                    entries[i]["THP"] = isTHP
                                    entries[i]["Changed"] = True
                            else: 
                                if entries[i]["THP"] == True:
                                    entries[i]["THP"] = isTHP
                                    entries[i]["Changed"] = True
                                newNumPages += 1
                                iterSize = pageSize
                        entries[i]["Checked"] = True 
                        entries[i]["XY"] = (col, row) 
                if col >= maxCol:
                    col = 0
                    row += 1
                else:
                    col += 1
                i += iterSize 
    return entries, row, col, newNumPages, newNumTHP

#--------------------------------------------------------------------------------------------------------------------#
def updateEnd(entries, vAdd, stopAdd, row, col):
    global iterSize
    newNumPages = 0
    newNumTHP = 0
    oldStopAdd = int(stopAdd, base=16)
    stopVAdd = int(vAdd[1], base=16)
    stopAddress = max(stopVAdd, oldStopAdd)
    with open(pagemapPath, 'rb') as frameFile: 
        with open(pageFlagPath, 'rb') as flagFile: 

            i = int(vAdd[0], base=16)
            while i < stopAddress:
                if i >= stopVAdd and i < oldStopAdd:
                    if i in entries and "Cell" in entries[i]: 
                        winCanvas.delete(entries[i]["Cell"])
                        if entries[i]["THP"] == True:
                            iterSize = hugePageSize
                            newNumTHP -= 1
                        else:
                            iterSize = pageSize
                            newNumPages -= 1
                        i += iterSize
                    continue
                else:
                    if i not in entries:
                        frameOffset = int((i / pageSize) * 8)
                        frameFile.seek(frameOffset)
                        try:
                            frame = struct.unpack('Q', frameFile.read(8))[0]
                        except:
                            break
                        if frame == 0:
                            isSwapped = False
                            isPresent = False
                            isTHP = False
                        else:
                            isSwapped = (frame & (1 << 62)) != 0
                            isPresent = (frame & (1 << 63)) != 0

                            flagOffset = (frame & ((1 << 54)-1)) * 8
                            flagFile.seek(flagOffset) 
                            try:
                                isTHP = (struct.unpack('Q', flagFile.read(8))[0] & (1 << 22)) != 0
                            except:
                                isTHP = False
                            if isTHP == True:
                                newNumTHP += 1
                                iterSize = hugePageSize
                            else: 
                                newNumPages += 1
                                iterSize = pageSize
                        entries[i] = {"Frame": frame, "Swap": isSwapped, "Present": isPresent, "THP": isTHP, "Changed": True, "XY": (col, row), "Checked": True}
                    else:
                        frameOffset = int((i / pageSize) * 8)
                        frameFile.seek(frameOffset)
                        try:
                            frame = struct.unpack('Q', frameFile.read(8))[0]
                        except:
                            break
                        if frame == 0:
                            if entries[i]["Frame"] != 0:
                                entries[i]["Frame"] = frame
                                entries[i]["Swap"] = False
                                entries[i]["Present"] = False
                                entries[i]["THP"] = False
                                entries[i]["Changed"] = True  
                            else:
                                entries[i]["Swap"] = False
                                entries[i]["Present"] = False
                                entries[i]["THP"] = False 
                        else: 
                            isSwapped = (frame & (1 << 62)) != 0
                            if entries[i]["Swap"] != isSwapped:
                                entries[i]["Swap"] = isSwapped
                                entries[i]["Changed"] = True
                            
                            isPresent = (frame & (1 << 63)) != 0
                            if entries[i]["Present"] != isPresent:
                                entries[i]["Present"] = isPresent
                                entries[i]["Changed"] = True

                            flagOffset = (frame & ((1 << 54)-1)) * 8
                            flagFile.seek(flagOffset) 
                            try:
                                isTHP = (struct.unpack('Q', flagFile.read(8))[0] & (1 << 22)) != 0
                            except:
                                isTHP = False
                            if isTHP == True:
                                newNumTHP += 1
                                iterSize = hugePageSize
                                if entries[i]["THP"] == False:
                                    entries[i]["THP"] = isTHP
                                    entries[i]["Changed"] = True
                            else: 
                                if entries[i]["THP"] == True:
                                    entries[i]["THP"] = isTHP
                                    entries[i]["Changed"] = True
                                newNumPages += 1
                                iterSize = pageSize
                        entries[i]["Checked"] = True 
                        entries[i]["XY"] = (col, row)  
                if col >= maxCol:
                    col = 0
                    row += 1
                else:
                    col += 1
                i += iterSize 
    return entries, row, col, newNumPages, newNumTHP

#--------------------------------------------------------------------------------------------------------------------#

def updatePages(pages):
    """
        Loads all data and draws every cell in the window
    """
    timer.tic()
    vAddList = getVaddress()
    if len(vAddList) == 0:
        messagebox.showinfo(title="Notice", message="Benchmark has terminated. Press 'Ok' to terminate monitor")
        mainWindow.quit()
        return
    iterSize = pageSize
    numTHP = 0
    numPages = 0
    row = 0
    col = 0 
    for vAdd in vAddList:

        checkedAdd = "{}-{}".format(vAdd[0], vAdd[1])
        if checkedAdd in pages:
            # Address range already in, only updating needed
            pages[checkedAdd], row, col, newNumPages, newNumTHP = justUpdate(pages[checkedAdd], vAdd, row, col)
            numPages += newNumPages
            numTHP += newNumTHP

        else:
            startPages = [] 
            stopPages = []  
            for addr in pages:
                start, stop = addr.split('-')
                startPages.append(start)
                stopPages.append(stop)

            startIndex = startPages.index(vAdd[0]) if vAdd[0] in startPages else -1 
            stopIndex = stopPages.index(vAdd[1]) if vAdd[1] in stopPages else -1 
            if startIndex != -1 and stopPages[startIndex] != vAdd[1]:
                # End address has changed. 
                oldIndex = "{}-{}".format(vAdd[0], stopPages[startIndex])
                if psu.pid_exists(pid) == False:
                    return
                pages[checkedAdd], row, col, newNumPages, newNumTHP = updateEnd(pages[oldIndex], vAdd, stopPages[startIndex], row, col)
                del pages[oldIndex]
                numPages += newNumPages
                numTHP += newNumTHP

            elif stopIndex != -1 and startPages[stopIndex] != vAdd[0]:
                # Start address has changed.
                oldIndex = "{}-{}".format(startPages[stopIndex], vAdd[1])
                if psu.pid_exists(pid) == False:
                    return
                pages[checkedAdd], row, col, newNumPages, newNumTHP = updateEnd(pages[oldIndex], vAdd, startPages[stopIndex], row, col)
                del pages[oldIndex]
                numPages += newNumPages
                numTHP += newNumTHP
            else:  
                if psu.pid_exists(pid) == False:
                    return
                with open(pagemapPath, 'rb') as frameFile: 
                    with open(pageFlagPath, 'rb') as flagFile: 
                        stopVAdd = int(vAdd[1], base=16)
                        i = int(vAdd[0], base=16)
                        entry = {} 
                        while i < stopVAdd:
                            frameOffset = int((i / pageSize) * 8)
                            frameFile.seek(frameOffset)
                            try:
                                frame = struct.unpack('Q', frameFile.read(8))[0]
                            except:
                                break
                            if frame == 0:
                                isSwapped = False
                                isPresent = False
                                isTHP = False

                            else:
                                isSwapped = (frame & (1 << 62)) != 0
                                isPresent = (frame & (1 << 63)) != 0

                                flagOffset = (frame & ((1 << 54)-1)) * 8
                                flagFile.seek(flagOffset) 
                                try:
                                    isTHP = (struct.unpack('Q', flagFile.read(8))[0] & (1 << 22)) != 0
                                except:
                                    isTHP = False
                                if isTHP == True and isPresent == True:
                                    numTHP += 1
                                    iterSize = hugePageSize
                                else: 
                                    numPages += 1
                                    iterSize = pageSize
                            entry[i] = {"Frame": frame, "Swap": isSwapped, "Present": isPresent, "THP": isTHP, "Changed": True, "XY": (col, row), "Checked": True}  
                            if col >= maxCol:
                                col = 0
                                row += 1
                            else:
                                col += 1
                            i += iterSize  

                        pageID = "{}-{}".format(vAdd[0], vAdd[1])
                        pages[pageID] = entry
        row += 1
        col = 0
    winCanvas.after(0, updateCells, pages)

#--------------------------------------------------------------------------------------------------------------------#

def updateCells(pages: dict):
    global step
    numPages = 0
    numTHP = 0
    totAllocMem = 0
    addressX = 5
    addressY = 1
    winLeftCanvas.delete("all")
    addVAdd = False
    for key, entries in pages.items():
        addVAdd = True

        for page in entries.values():
            if "THP" in page and page["THP"] == True:
                numTHP +=1
            else: 
                numPages += 1
            col = page["XY"][0]
            row = page["XY"][1]

            x1 = col*10+2
            x2 = col*10+10
            y1 = row*10+2
            y2 = row*10+10
            addressY = y1+10

# If a cell has not been created for the page, create it
            if "Cell" not in page:
                if addVAdd == True:
                    winLeftCanvas.create_text(addressX, addressY, text=key.split('-')[0], anchor=tk.NW, font=(None, 7))
                    addVAdd = False
                if page["Frame"] != 0:
                    if page["THP"] == True:
                        page["Cell"] = winCanvas.create_rectangle(x1, y1, x2, y2, fill='yellow', outline='red', width=1)
                        page["Changed"] = True
                    elif page["Present"] == True:
                        page["Cell"] = winCanvas.create_rectangle(x1, y1, x2, y2, fill='lightgreen', outline='red', width=1)
                        page["Changed"] = True 
                    elif page["Swap"] == True:
                        page["Cell"] = winCanvas.create_rectangle(x1, y1, x2, y2, fill='blue', outline='red', width=1)
                        page["Changed"] = True
                    else:
                        page["Cell"] = winCanvas.create_rectangle(x1, y1, x2, y2, fill='lightgrey', outline='red', width=1)
                        page["Changed"] = True
                else:
                    page["Cell"] = winCanvas.create_rectangle(x1, y1, x2, y2, fill='lightgrey', outline='red', width=1)
                    page["Changed"] = True

                    

# If a cell has been created for the page, update it if needed
            else:
                if page["Checked"] == False:
                    # Page was not in last update, delete it
                    winCanvas.delete(page["Cell"]) 
                    if "THP" in page and page["THP"] == True:
                        numTHP -=1
                    else: 
                        numPages -= 1
                    del page
                    
                    continue
                else:
                    if addVAdd == True:
                        winLeftCanvas.create_text(addressX, addressY, text=key.split('-')[0], anchor=tk.NW, font=(None, 7))
                        addVAdd = False
                    if page["Frame"] == 0:
                        if page["Changed"] == True:
                            winCanvas.itemconfigure(page["Cell"], fill='lightgrey', outline='red')
                            winCanvas.coords(page["Cell"], x1, y1, x2, y2)
                            page["Changed"] = False 
                        else:
                            winCanvas.itemconfigure(page["Cell"], fill='lightgrey', outline='grey')
                            winCanvas.coords(page["Cell"], x1, y1, x2, y2)

                    elif page["THP"] == True:
                        if page["Changed"] == True:
                            winCanvas.itemconfigure(page["Cell"], fill='yellow', outline='red')
                            winCanvas.coords(page["Cell"], x1, y1, x2, y2)
                            page["Changed"] = False 
                        else:
                            winCanvas.itemconfigure(page["Cell"], fill='yellow', outline='grey')
                            winCanvas.coords(page["Cell"], x1, y1, x2, y2)

                    elif page["Present"] == True:
                        if page["Changed"] == True:
                            winCanvas.itemconfigure(page["Cell"], fill='lightgreen', outline='red')
                            winCanvas.coords(page["Cell"], x1, y1, x2, y2)
                            page["Changed"] = False 
                        else:
                            winCanvas.itemconfigure(page["Cell"], fill='lightgreen', outline='grey')
                            winCanvas.coords(page["Cell"], x1, y1, x2, y2)

                    elif page["Swap"] == True:
                        if page["Changed"] == True:
                            winCanvas.itemconfigure(page["Cell"], fill='blue', outline='red')
                            winCanvas.coords(page["Cell"], x1, y1, x2, y2)
                            page["Changed"] = False 
                        else:
                            winCanvas.itemconfigure(page["Cell"], fill='blue', outline='grey')
                            winCanvas.coords(page["Cell"], x1, y1, x2, y2)

                    else:
                        if page["Changed"] == True:
                            winCanvas.itemconfigure(page["Cell"], fill='lightgrey', outline='red')
                            winCanvas.coords(page["Cell"], x1, y1, x2, y2)
                            page["Changed"] = False 
                        else:
                            winCanvas.itemconfigure(page["Cell"], fill='lightgrey', outline='grey')
                            winCanvas.coords(page["Cell"], x1, y1, x2, y2)
        
            page["Checked"] = False

    totAllocMem = updateTotAllocMem()
    totVAllocMem = updateTotVAllocMem()

    winBotCanvas.itemconfigure(tNumTHP, text="Nr of THP(2MB): {}".format(numTHP))
    winBotCanvas.itemconfigure(tNumPage, text="Nr of Pages(4kB): {}".format(numPages))
    winBotCanvas.itemconfigure(tAllMem, text="Total allocated memory: {:.2f}MB".format(totAllocMem / 1000))
    winBotCanvas.itemconfigure(tAllTHP, text="Total allocated THP: {:.2f}MB".format(numTHP*hugePageSize / 1024 / 1000))
    winBotCanvas.itemconfigure(tAllVMem, text="Total allocated V-memory: {:.2f}MB".format(totVAllocMem / 1000))
    winBotCanvas.itemconfigure(updSincStart, text="Updates since start: {}".format(step))
    winCanvas.configure(scrollregion=winCanvas.bbox("all"))
    winLeftCanvas.configure(scrollregion=winLeftCanvas.bbox("all"))
    elapsed = timer.tocvalue()
    # elapsed = "{:.2f}".format(timer.tocvalue())
    data[step] = {"THP": numTHP, "Pages": numPages, "TotAlloc": totAllocMem/1000, "THPAlloc": numTHP*hugePageSize / 1024 / 1024, "TotVAlloc": totVAllocMem/1000, "Time": elapsed} 
    step += 1

    winCanvas.after(500, updatePages, pages)


#--------------------------------------------------------------------------------------------------------------------#


if __name__ == "__main__":
    timer = TicToc()
    saveFileArgs = ""
    if sys.argv[1][-3:] == ".py":
        bench = sp.Popen(['python3', '{}/benchmarks/{}'.format(cwd, sys.argv[1]), sys.argv[2]], shell=False) 
        saveFileArgs = "_"+sys.argv[2] 
        timer.tic()
    else:
        program = str(sys.argv[1])
        test = [] 

        test.append('{}/benchmarks/{}'.format(cwd, program))
        for x in sys.argv[2:]:
            if '/' in x:
                y = x.split('/')
                saveFileArgs += "_{}".format(str(y[-1]))
            else:
                saveFileArgs += "_{}".format(x)
            test.append(x) 
        bench = sp.Popen([x for x in test])
        timer.tic()
    pid = bench.pid 
    pagemapPath = "/proc/{0}/pagemap".format(pid)
    time.sleep(0.5)
    pages = {}
    winCanvas.after(100, updatePages, pages)
    mainWindow.mainloop()
    bench.kill()
    benchFileName = sys.argv[1].split('/')[-1] 

    a_file = open("stored_data/{}{}_data.json".format(benchFileName,saveFileArgs), "w")
    json.dump(data, a_file)
    a_file.close()
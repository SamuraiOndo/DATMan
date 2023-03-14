from binary_reader import BinaryReader
import sys
from pathlib import Path
import os
import re
import json
Mypath = Path(sys.argv[1])
directory = str(Mypath.resolve().parent)
Myfilename = Mypath.name
w = BinaryReader()
w.set_endian(False)
unique_id = 0
if(Mypath.is_file()):
    path = Mypath.open("rb")
    reader = BinaryReader(path.read())
    w = BinaryReader()
    w.set_endian(False)
    reader.set_endian(False) # big endian
    reader.seek(0)
    tlfdcount = reader.read_uint32()
    header = {
        "Count": tlfdcount,
    }
    reader.seek(0x10)
    for i in range(tlfdcount):
        pointer = reader.read_uint32()
        size1 = reader.read_uint32()
        indices = reader.read_uint32()
        try:
            identifier = reader.read_str(4)
        except:
            continue
        section = {
            "Identifier": identifier,
        }
        stay = reader.pos()
        reader.seek(pointer)
        count = reader.read_uint32()
        try:
            indentifier1 = reader.read_str(4)
        except:
            reader.seek(4,1)
            indentifier1 = "UNK"
        reader.read_uint32(2)
        p = 0
        if count != 0:
            for j in range(count):
                pointer2 = reader.read_uint32()
                size2 = reader.read_uint32()
                hash = reader.read_uint32()
                filename = f"{i}-{j}"
                if (size2 == 0):
                    filename = "BLANK"
                stay2 = reader.pos()
                output_path = directory / Path(Myfilename + ".unpack")
                output_path.mkdir(parents=True, exist_ok=True)
                offset = pointer + pointer2
                reader.seek(offset)
                if (size2 != 0):
                    fileData = reader.read_bytes(size2)
                    readertemp = BinaryReader(fileData)
                    #stolen from retraso
                    try:
                        readertemp.seek(0)
                        newfile_magic = readertemp.read_str(3)
                        if (len(newfile_magic) == 3):
                            magic_is_bad = any(not c.isalnum() for c in newfile_magic)
                            if magic_is_bad:
                                raise Exception("bad 3 char magic")
                            else:
                                filename += f".{newfile_magic}"
                        else:
                            raise Exception("magic length less than 3")
                    except:
                        filename += ".dat"
                    output_file = output_path / (filename)
                    fe = open(output_file, "wb")
                    fe.write(fileData)
                    print("writing to", output_file, offset, size2)
                    fe.close()
                    unique_id += 1
                reader.seek(stay2)
                reader.read_uint32(1)
                file = {
                    "Hash?": hash,
                    "File Name": filename,
                }
                section.update({p: file})
                p+=1
            reader.seek(stay)
            
        else:
            output_path = directory / Path(Myfilename + ".unpack")
            output_path.mkdir(parents=True, exist_ok=True)
            reader.seek(stay)
        header.update({f"Section {i}": section})
    output_file = Path(sys.argv[1] + ".unpack") / ("manifest.json")
    filejson = open(output_file, "w")
    filejson.write(json.dumps(header,ensure_ascii = False, indent = 2))
    filejson.close()
if(Mypath.is_dir()):
    size2 = 0
    f = open((sys.argv[1] + "/manifest.json"), "r")
    p = json.loads(f.read())
    foldercount = len(p) - 1
    folderlist = list()
    w.write_uint32(foldercount)
    newarchivename = sys.argv[1].replace('.unpack','')
    newarchive = open(newarchivename, "wb")
    listOfFiles = list()
    for i in range(foldercount):
        folderlist.append(p[f"Section {i}"]["Identifier"])
    print(folderlist)
    w.align(0x10)
    for i in range(foldercount):
        if i == 0:
            pointer = 16*foldercount+16
        else:
            pointer = 16*foldercount+16+size2
        w.write_uint32(pointer)
        listOfFilesInFolder = list()
        currentfolder = Mypath / folderlist[i]
        hashes = list()
        for j in range(len(p[f"Section {i}"])-1):
            listOfFilesInFolder.append(sys.argv[1] + "\\" + p[f"Section {i}"][str(j)]["File Name"])
            hashes.append(p[f"Section {i}"][str(j)]["Hash?"])
        identifier = folderlist[i]
        size = 0
        for elem in listOfFilesInFolder:
            if (elem != (sys.argv[1] + "\\" + "BLANK")):
                size += os.path.getsize(elem)
                test = 16 - (size % 16)
                if (test != 16):
                    size += test
        size2 += size+((len(listOfFilesInFolder)*16)+16)
        padTo16 = 16 - (size2%16)
        if (padTo16 != 16):
            size2 += padTo16
        padTo16ForWriting = (size+((len(listOfFilesInFolder)*16)+16)) % 16
        #w.write_uint32(size+((len(listOfFilesInFolder)*16)+16) + padTo16ForWriting)
        w.write_uint32(0)
        w.write_uint32(i+1)
        if identifier != "unk":
            w.write_str_fixed(identifier,4)
        else:
            w.write_uint32(0)
        stay = w.pos()
        w.align(pointer)
        w.seek(pointer)
        w.write_uint32(len(listOfFilesInFolder))
        print(identifier)
        if identifier != "unk":
            w.write_str_fixed(identifier,4)
        else:
            w.write_uint32(0)
        w.write_uint32(0)
        w.write_uint32(0)
        size3 = 0
        k = 0
        for elem in listOfFilesInFolder:
            test3 = (16*len(listOfFilesInFolder)+16+size3)%16
            w.write_uint32(16*len(listOfFilesInFolder)+16+size3)
            hash = elem.split("~")
            if (elem != (sys.argv[1] + "\\" + "BLANK")):
                w.write_uint32(os.path.getsize(elem))
            else:
                w.write_uint32(0)
            w.write_uint32(int(hashes[k]))
            k+=1
            w.write_uint32(0)
            if (elem != (sys.argv[1] + "\\" + "BLANK")):
                size3 += os.path.getsize(elem)
            if ((16 - (size3 % 16)) != 16):
                size3 += (16 - (size3 % 16))
        for elem in listOfFilesInFolder:
            if (elem != (sys.argv[1] + "\\" + "BLANK")):
                file = open(elem, "rb")
                w.write_bytes(file.read())
            if (w.pos() % 16 != 0):
                w.pad(16 - (w.pos() % 16))
            file.close()
        secSize = w.pos()
            
            

        w.seek(stay-12)
        w.write_uint32(secSize-pointer)
        w.seek(stay)
        listOfFilesInFolder.clear()
    newarchive.write(w.buffer())
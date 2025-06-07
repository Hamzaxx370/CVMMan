import os
from binary_reader import BinaryReader
import lzss
import json
import sys

SectorSize = 2048
O1ENG = 1095680
O2ENG = 6144

def WriteCVMDIR(path):
    OGREDIRLIST = []
    os.chdir(path)
    Name = os.path.basename(path)
    if not os.path.exists("main.json"):
        print("No main.json found")
        sys.exit()
    JSON = open("main.json",'r')
    Main = json.load(JSON)
    JSON.close()
    OGREDIR = open(Name + ".BIN",'wb')
    writer = BinaryReader()
    CVMHeader = open(Name + ".cvmhdr",'rb')
    Header1 = CVMHeader.read()
    DIRHeader = open(Name + ".dirhdr",'rb')
    Header2 = DIRHeader.read()
    CVM = open(f"OGRE{int (Main["Ogre Number"])}.CVM","wb")
    CVM.write(Header1)
    for dirpath in Main["Directories"]:
        DirWriter = BinaryReader()
        print(dirpath)
        os.chdir(dirpath)
        DirJSON = open("manifest.json",'rb')
        DirInfo = json.load(DirJSON)
        DirWriter.write_uint32(len(DirInfo["Files"]))
        DirWriter.write_uint32(len(DirInfo["Files"]))
        DirWriter.write_uint32(DirInfo["Files"][0]["Sector"])
        DirWriter.write_str("#DirLst#")
        DirWriter.pad(4)
        for Info in DirInfo["Files"]:
            Type = bytes.fromhex(Info["Unknown"])
            if Type[0] == 2:
                DirWriter.write_uint32(Info["Size"])
                DirWriter.pad(4)
                DirWriter.write_uint32(Info["Sector"])
                start = DirWriter.pos()
                DirWriter.write_bytes(Type)
                DirWriter.write_str(Info["Name"])
                DirWriter.pad(36-(DirWriter.pos()-start))
            else:
                File = open(Info["Name"],'rb')
                Data = File.read()
                File.close()
                Sector = CVM.tell() - 6144
                CVM.write(Data)
                CVM.write(b'\x00' * ((2048 - (CVM.tell()%2048)) %2048))
                print(Info["Name"])
                DirWriter.write_uint32(len(Data))
                DirWriter.pad(4)
                DirWriter.write_uint32(int(Sector / 2048))
                start = DirWriter.pos()
                DirWriter.write_bytes(Type)
                DirWriter.write_str(Info["Name"])
                DirWriter.pad(36-(DirWriter.pos()-start))
        DirWriter.write_str("GN")
        DirWriter.pad(38)
        Len1 = DirWriter.pos()
        AVLZ = lzss.compress(bytes(DirWriter.buffer()))
        OGREDIRLIST.append((DirInfo["Directory Name"],AVLZ,Len1,len(AVLZ)+12,len(DirInfo["Files"])))
    writer.write_bytes(Header2)
    writer.write_int32(len(OGREDIRLIST))
    writer.write_int32(int (Main["Unk Value"]))
    writer.pad(56)
    for dir in OGREDIRLIST:
        Pos = writer.pos()
        writer.write_str(dir[0])
        writer.pad((56-(writer.pos()-Pos)))
        writer.write_uint32(dir[4])
        writer.write_uint32(0)
    Pointers = []
    for dir in OGREDIRLIST:
        Pointers.append(writer.pos())
        writer.write_str("AVLZ")
        writer.write_int32(dir[2])
        writer.write_int32(dir[3])
        writer.write_bytes(dir[1])
        writer.align(64)
    for i in range(len(OGREDIRLIST)):
        writer.seek((128+(64*i))+60)
        writer.write_int32(Pointers[i])
    OGREDIR.write(writer.buffer())
    OGREDIR.close()
    DirJSON.close()
    CVMHeader.close()
    CVM.close()
    DIRHeader.close()
def GetAVLZFiles(reader,Offset,Contents,CVM):
    List = []
    returnpos = reader.pos()
    reader.seek(Offset)
    AVLZString = reader.read_str(4)
    if AVLZString != "AVLZ":
        print("AVLZ Error")
        sys.exit()
        return
    Size1 = reader.read_uint32()
    Size2 = reader.read_uint32()
    AVLZ = reader.read_bytes(Size2 - 12)
    Info = lzss.decompress(AVLZ)
    Ireader = BinaryReader(Info)
    Count1 = Ireader.read_uint32()
    Count2 = Ireader.read_uint32()
    SectorStart = Ireader.read_uint32()
    Identifier = Ireader.read_str(8)
    Ireader.read_bytes(4)
    if Identifier != "#DirLst#":
        print("Corrupt AVLZ")
        sys.exit()
        return
    for i in range(Contents):
        Size = Ireader.read_uint32()
        Ireader.read_bytes(4)
        Sector = Ireader.read_uint32()
        Unknown = Ireader.read_bytes(2)
        Name = Ireader.read_str(34)
        print(Name)
        Entry = {
            "Name" : Name,
            "Unknown" : "".join(f'{byte:02x}' for byte in Unknown),
            "Sector" : Sector,
            "Size" : Size
        }
        if Unknown[0] != 2:
            CVM.seek((Sector * 2048)+6144,0)
            new = open(Name,"wb")
            print(Size)
            file = CVM.read(Size)
            new.write(file)
            new.close()
        List.append(Entry)
    reader.seek(returnpos)
    return List

def ReadOGREDIR(path,cvmpath):
    os.chdir(os.path.dirname(cvmpath))
    Directories = []
    DIR = open(path,'rb')
    CVM = open(cvmpath,'rb')
    reader = BinaryReader(DIR.read())
    Header = reader.read_bytes(64)
    DirCount = reader.read_uint32()
    Unk = reader.read_uint32()
    JSON = {
        "Directories" : [],
        "Unk Value" : Unk,
        "Ogre Number" : input("Ogre Number\n")
    }
    reader.seek(128)
    ODIRName = os.path.basename(path)
    os.chdir(os.path.dirname(path))
    if not os.path.exists(os.path.splitext(ODIRName)[0]):
        os.mkdir(os.path.splitext(ODIRName)[0],True)
    os.chdir(os.path.splitext(ODIRName)[0])
    CVMHdr = CVM.read(43008)
    CVMHDR = open(os.path.splitext(ODIRName)[0]+ ".cvmhdr",'wb')
    CVMHDR.write(CVMHdr)
    DirHDR = open(os.path.splitext(ODIRName)[0]+ ".dirhdr",'wb')
    DirHDR.write(Header)
    FullPath = os.getcwd()
    for i in range(DirCount):
        DirName = reader.read_str(56)
        Contents = reader.read_uint32()
        AVLZOffset = reader.read_uint32()
        DirPath = os.path.join(FullPath,DirName.lstrip('/'))
        print(FullPath,DirPath)
        JSON["Directories"].append(DirPath)
        if not os.path.exists(DirPath):
            os.mkdir(DirPath,True)
        os.chdir(DirPath)
        List = GetAVLZFiles(reader,AVLZOffset,Contents,CVM)
        JSONE = {
            "Directory Name" : DirName,
            "Files" : List
        }
        JSONFile = open("manifest.json",'w')
        json.dump(JSONE,JSONFile,indent=4)
        JSONFile.close()
        os.chdir(FullPath)
    JSONFile = open("main.json",'w')
    json.dump(JSON,JSONFile,indent=4)
    JSONFile.close()
    DIR.close()
    CVM.close()
def main():
    files = sys.argv[1:]
    for file in files:
        if os.path.splitext(file)[1].lower() == ".cvm":
            DIR = input("Enter DIR Path \n")
            if os.path.exists(DIR):
                ReadOGREDIR(DIR,file)
            else:
                print("Invalid DIR Path")
        elif os.path.isdir(file):
            WriteCVMDIR(file)
if __name__ == "__main__":
    main()
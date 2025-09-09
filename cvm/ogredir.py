from binary_reader import BinaryReader
import os
import lzss
import json
import sys

class OgreDirFile:
    Size: int
    Sector: int
    Unk: int
    Name: str #34
    
    def __init__(self):
        self.Size = 0
        self.Sector = 0
        self.Unk = 0
        self.Name = ""
        
    def Read(self,reader: BinaryReader):
        self.Size = reader.read_int32()
        reader.read_int32()
        self.Sector = reader.read_int32()
        self.Unk = reader.read_uint16()
        self.Name = reader.read_str(34).rstrip('\x00')
    def Write(self, writer: BinaryReader):
        writer.write_int32(self.Size)
        writer.write_int32(0)
        writer.write_int32(self.Sector)
        start = writer.pos()
        writer.write_uint16(self.Unk)
        writer.write_str(self.Name)
        writer.pad(36-(writer.pos()- start))

class AVLZObj:
    DSize: int
    CSize: int
    Data: bytes
    
    def __init__(self):
        self.DSize = 0
        self.CSize = 0
        self.Data = b"\x00"

class OgreDirEntry:
    Name: str #56 
    EntryCount: int
    SectorStart: int
    Magic: str
    Files: list[OgreDirFile]
    
    def __init__(self):
        self.Name = ""
        self.EntryCount = 0
        self.SectorStart = 0
        self.Magic = "#DirLst#"
        self.Files = []
        
    def Read(self, reader: BinaryReader):
        self.Name = reader.read_str(56).rstrip('\x00')
        self.EntryCount = reader.read_int32()
        Offset = reader.read_int32()
        returnpos = reader.pos()
        reader.seek(Offset)
        Magic = reader.read_str(4)
        DecompressedSize = reader.read_int32()
        Size = reader.read_int32()
        Compressed = reader.read_bytes(Size - 12)
        Temp = lzss.decompress(Compressed)
        dirreader = BinaryReader(Temp)
        self.EntryCount = dirreader.read_int32()
        dirreader.read_int32()
        self.SectorStart = dirreader.read_int32() 
        self.Magic = dirreader.read_str(8)
        dirreader.read_bytes(4)
        
        for i in range(self.EntryCount):
            File = OgreDirFile()
            File.Read(dirreader)
            self.Files.append(File)
            
        reader.seek(returnpos)
    def Write(self, writer: BinaryReader, offsets: list[int]):
        pos = writer.pos()
        writer.write_str(self.Name)
        writer.pad((56-(writer.pos()-pos)))
        writer.write_int32(len(self.Files))
        offsets.append(writer.pos())
        writer.write_int32(0)
        
        dirwriter = BinaryReader()
        dirwriter.write_int32(len(self.Files))
        dirwriter.write_int32(len(self.Files))
        dirwriter.write_int32(self.SectorStart)
        dirwriter.write_str(self.Magic)
        dirwriter.write_int32(0)
        
        for file in self.Files:
            file.Write(dirwriter)
        
        dirwriter.write_str("GN")
        dirwriter.pad(38)
        avlz_obj = AVLZObj()
        avlz_obj.DSize = dirwriter.pos()
        avlz_obj.Data = lzss.compress(bytes(dirwriter.buffer()))
        avlz_obj.CSize = len(avlz_obj.Data) + 12
        
        return avlz_obj
        
class OgreDir:
    UnkHeader: bytes
    DirCount: int
    UnkInt: int
    Dirs: list[OgreDirEntry]
    
    def __init__(self):
        self.UnkHeader = bytes(64)
        self.DirCount = 0
        self.UnkInt = 0
        self.Dirs = []
    
    def Read(self,reader: BinaryReader, MainPath:str,fileName: str):
        self.UnkHeader = reader.read_bytes(64)
        self.DirCount = reader.read_int32()
        self.UnkInt = reader.read_int32()
        
        if (MainPath != ""):
            with open(os.path.join(MainPath,f"{fileName}.dhdr"),"wb") as f:
                f.write(self.UnkHeader)
                
        Base = 128
        
        for i in range(self.DirCount):
            reader.seek(Base + (i * 64))
            Dir = OgreDirEntry()
            Dir.Read(reader)
            self.Dirs.append(Dir)
    def Write(self, writer: BinaryReader):
        writer.write_bytes(self.UnkHeader)
        writer.write_int32(self.DirCount)
        writer.write_int32(self.UnkInt)
        writer.pad(128 - (72))
        
        avlz_objs = []
        offsets = []
        avlz_offsets = []
        
        for dir in self.Dirs:
            avlz_objs.append(dir.Write(writer,offsets))
        
        for avlz_obj in avlz_objs:
            avlz_offsets.append(writer.pos())
            writer.write_str("AVLZ")
            writer.write_int32(avlz_obj.DSize)
            writer.write_int32(avlz_obj.CSize)
            writer.write_bytes(avlz_obj.Data)
            writer.align(64)
        for i in range(len(offsets)):
            writer.seek(offsets[i])
            writer.write_int32(avlz_offsets[i])  
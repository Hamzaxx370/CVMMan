import sys
import os
import argparse
import json
from collections import defaultdict
from binary_reader import BinaryReader
from cvm.ogredir import OgreDir, OgreDirEntry, OgreDirFile

Ogre1Media = {
    "MEDIA":  "OGRE.CVM",
    "MEDIA2": "OGRE2.CVM",
    "MEDIA3": "OGRE3.CVM",
    "MEDIA4": "OGRE4.CVM"
}

Ogre1Dir = {
    "MEDIA":  "OGREDIR.BIN",
    "MEDIA2": "OGREDIR2.BIN",
    "MEDIA3": "OGREDIR3.BIN",
    "MEDIA4": "OGREDIR4.BIN"
}

Ogre2Media1 = {
    "MEDIA":  "OGRE1_1.CVM",
    "MEDIA2": "OGRE2_1.CVM",
    "MEDIA3": "OGRE3_1.CVM",
    "MEDIA4": "OGRE4_1.CVM",
    "MEDIA5": "OGRE5_1.CVM"
}

Ogre2Dir1 = {
    "MEDIA":  "DIR1_1.BIN",
    "MEDIA2": "DIR2_1.BIN",
    "MEDIA3": "DIR3_1.BIN",
    "MEDIA4": "DIR4_1.BIN",
    "MEDIA5": "DIR5_1.BIN"
}

Ogre2Media2 = {
    "MEDIA":  "OGRE1_2.CVM",
    "MEDIA2": "OGRE2_2.CVM",
    "MEDIA3": "OGRE3_2.CVM",
    "MEDIA4": "OGRE4_2.CVM",
    "MEDIA5": "OGRE5_2.CVM"
}

Ogre2Dir2 = {
    "MEDIA":  "DIR1_2.BIN",
    "MEDIA2": "DIR2_2.BIN",
    "MEDIA3": "DIR3_2.BIN",
    "MEDIA4": "DIR4_2.BIN",
    "MEDIA5": "DIR5_2.BIN"
}

class PatchFile:
    RealPath: str
    GamePath: str
    Size: int
    Media: str
    TargetSize: int
    TargetSector: int
    CanPatch: bool
    
    def __init__(self):
        self.RealPath = ""
        self.GamePath = ""
        self.Size = 0
        self.Media = ""
        self.TargetSize = 0
        self.TargetSector = 0
        self.CanPatch = False

def PatchDef(cvm_file,new_cvm: str, dir: OgreDir,new_dir: str, patches: PatchFile):
    for pf in patches:
        cvm_file.seek((pf.TargetSector * 2048) + 6144)
        with open(pf.RealPath,"rb") as f:
            cvm_file.write(f.read())
    
def PatchRebuild(cvm_file,new_cvm: str, dir: OgreDir,new_dir: str, patches: PatchFile):
    patch_lookup = {pf.GamePath.lower(): pf for pf in patches}
    with open(new_cvm, "wb") as out:
        cvm_file.seek(0)
        out.write(cvm_file.read(43008))
        out.write(b'\x00' * ((2048 - (out.tell()%2048)) %2048))

        for folder in dir.Dirs:
            out.write(b'\x00' * ((2048 - (out.tell()%2048)) %2048))
            folder.SectorStart = (out.tell() - 6144) // 2048
            for file in folder.Files:
                game_path = f"{folder.Name}{file.Name}".lower()
                OgSector = file.Sector
                file.Sector = (out.tell() - 6144) // 2048

                if game_path in patch_lookup:
                    pf = patch_lookup[game_path]
                    with open(pf.RealPath, "rb") as src:
                        data = src.read()
                        file.Size = len(data)
                        out.write(data)
                else:
                    cvm_file.seek(OgSector * 2048 + 6144)
                    data = cvm_file.read(file.Size)
                    file.Size = len(data)
                    out.write(data)

                out.write(b'\x00' * ((2048 - (out.tell()%2048)) %2048))

        # update OgreDir
        dir.DirCount = len(dir.Dirs)
        with open(new_dir, "wb") as d:
            writer = BinaryReader()
            dir.Write(writer)
            d.write(writer.buffer())
    
def main():
    parser = argparse.ArgumentParser(description="Yakuza PS2 Patcher")
    parser.add_argument("-p","--patch",help="Patch mode", action="store_true")
    parser.add_argument("--game",help="Game, either Y1 or Y2_1, Y2_2")
    parser.add_argument("--patch-dir",help="Patch folder containing Media folders")
    parser.add_argument("--game-dir",help="Folder containing all game files")
    
    parser.add_argument("-r","--repack", help="Repack mode", action="store_true")
    
    parser.add_argument("--list-file", help="Input list for repack")
    
    parser.add_argument("-u","--unpack", help="Unpack mode", action="store_true")
    
    parser.add_argument("--dir-file", help="OgreDir path")
    parser.add_argument("--cvm-file", help="CVM path")
    
    args = parser.parse_args()
    
    if args.patch:
        if args.game.upper() == "Y1":
            cvm_map = Ogre1Media
            dir_map = Ogre1Dir
        elif args.game.upper() == "Y2_1":
            cvm_map = Ogre2Media1
            dir_map = Ogre2Dir1
        elif args.game.upper() == "Y2_2":
            cvm_map = Ogre2Media2
            dir_map = Ogre2Dir2
        
        patch_root = os.path.abspath(args.patch_dir)
        game_root = os.path.abspath(args.game_dir)
        
        patch_files = []
        ogre_dirs = {}
        
        for media,dirfile in dir_map.items():
            dir_path = os.path.join(game_root, dirfile)
            with open(dir_path,"rb") as f:
                reader = BinaryReader(f.read())
                dir_obj = OgreDir()
                dir_obj.Read(reader,"",os.path.splitext(dirfile)[0])
                ogre_dirs[media] = dir_obj
        
        for root,dirs,files in os.walk(patch_root):
            for f in files:
                file = PatchFile()
                file.RealPath = os.path.join(root,f)
                file.GamePath = os.path.relpath(file.RealPath,patch_root).replace("\\","/")
                file.GamePath =  "/" + file.GamePath
                file.Size = os.path.getsize(file.RealPath)
                file.Media = file.GamePath.lstrip("/").split("/",1)[0]
                patch_files.append(file)
        
        for pf in patch_files:
            dir_obj = ogre_dirs[pf.Media]
            Found  = False
            
            for folder in dir_obj.Dirs:
                for file in folder.Files:
                    game_path = f"{folder.Name}{file.Name}"
                    if game_path.lower() == pf.GamePath.lower():
                        pf.TargetSize = file.Size
                        pf.TargetSector = file.Sector
                        pf.CanPatch = pf.Size <= file.Size
                        Found = True
                        print(f"File found: {pf.GamePath}")
                        
            if not Found:
                print(f"File not found: {pf.GamePath}")
                return
            
        media_groups = defaultdict(list) 
        for pf in patch_files:
            media_groups[pf.Media].append(pf)
        
        os.chdir(game_root)
        
        for media,files in media_groups.items():
            if all(pf.CanPatch for pf in files):
                with open(os.path.join(game_root,cvm_map[media]),"rb+") as c:
                    print(f"Patching in place: {os.path.join(game_root,cvm_map[media])}")
                    PatchDef(c,f"NEW_{cvm_map[media]}", ogre_dirs[media],f"NEW_{dir_map[media]}",files)
            else:
                print(f"Rebuilding as NEW_: {os.path.join(game_root,cvm_map[media])}")
                with open(os.path.join(game_root,cvm_map[media]),"rb+") as c:
                    PatchRebuild(c,f"NEW_{cvm_map[media]}", ogre_dirs[media],f"NEW_{dir_map[media]}",files)
        
            
    elif args.repack:
        list_abs = os.path.abspath(args.list_file)
        dirname = os.path.dirname(list_abs)
        print("Directory:", dirname)
        os.chdir(dirname)
        
        list_file = open(list_abs,"r")
        
        list_obj = json.load(list_file)
        
        dir_hdr = open(f"{list_obj['CVM Name']}.dhdr","rb")
        cvm_hdr = open(f"{list_obj['CVM Name']}.chdr","rb")
        
        dir_obj = OgreDir()
        dir_obj.UnkHeader = dir_hdr.read()
        
        with open(f"{list_obj['OGREDIR Name']}.BIN","wb") as d, open(f"{list_obj['CVM Name']}.cvm","wb") as c:
            writer = BinaryReader()

            c.write(cvm_hdr.read())
            c.write(b'\x00' * ((2048 - (c.tell()%2048)) %2048))
            
            for folder in list_obj["Directories"]:
                os.chdir(os.path.join(dirname,folder["Name"].lstrip("/\\")))
                c.write(b'\x00' * ((2048 - (c.tell()%2048)) %2048))
                folder_obj = OgreDirEntry()
                folder_obj.Name = folder["Name"]
                folder_obj.EntryCount = len(folder["Files"])
                folder_obj.SectorStart = (c.tell() - 6144) // 2048
                for file in folder["Files"]:
                    file_obj = OgreDirFile()
                    file_obj.Name = file["Name"]
                    file_obj.Sector = (c.tell() - 6144) // 2048
                    file_obj.Unk = int.from_bytes(bytes.fromhex(file["Unk"]),byteorder="little")
                    if (bytes.fromhex(file["Unk"])[0] != 2):
                        with open(file["Name"], "rb") as f:
                            bytesf = f.read()
                            file_obj.Size = len(bytesf)
                            c.write(bytesf)
                    else:
                        file_obj.Size = 2048
                        c.write(b"\x00" * 2048)
                    c.write(b'\x00' * ((2048 - (c.tell()%2048)) %2048))
                    folder_obj.Files.append(file_obj)
                dir_obj.Dirs.append(folder_obj)
            dir_obj.DirCount = len(dir_obj.Dirs)
            dir_obj.UnkInt = list_obj["Unk Value"]
            dir_obj.Write(writer)
            d.write(writer.buffer())
                
                
                
            
        list_file.close()
        dir_hdr.close()
        cvm_hdr.close()
        
        
    elif args.unpack:
        with open(args.dir_file, "rb") as d, open(args.cvm_file, "rb") as c:
            cvp_abs = os.path.abspath(args.cvm_file)
            dirname = os.path.dirname(cvp_abs)
            print("Directory:", dirname)
            
            main_path = os.path.splitext(os.path.basename(cvp_abs))[0]
            main_path = os.path.join(dirname, main_path)
            os.makedirs(main_path, exist_ok=True)
            
            with open(os.path.join(main_path,f"{os.path.splitext(args.cvm_file)[0]}.chdr"),"wb") as ch:
                ch.write(c.read(43008))
            
            reader = BinaryReader(d.read())
            dir_obj = OgreDir()
            dir_obj.Read(reader, main_path,os.path.splitext(args.cvm_file)[0])
            
            json_obj = {
                "CVM Name" : os.path.splitext(args.cvm_file)[0],
                "OGREDIR Name" : os.path.splitext(args.dir_file)[0],
                "Unk Value" : dir_obj.UnkInt,
                "Directories" : [],
            }
            
            for folder in dir_obj.Dirs:
                j = {
                    "Name" : folder.Name,
                    "Files" : []
                }
                folder_path = os.path.join(main_path, folder.Name.lstrip("/\\"))
                os.makedirs(folder_path, exist_ok=True)
                for file in folder.Files:
                    c.seek((file.Sector * 2048) +6144)
                    print(file.Name)
                    j["Files"].append({
                        "Name" : file.Name,
                        "Unk" : file.Unk.to_bytes(2,byteorder="little").hex()
                    })
                    if file.Unk.to_bytes(2,byteorder="little")[0] != 2:
                        with open(os.path.join(folder_path,file.Name),"wb") as o:
                            o.write(c.read(file.Size))
                json_obj["Directories"].append(j)
        os.chdir(main_path)
        with open("list.json","w") as j:
            json.dump(json_obj,j,indent=4)
if __name__ == "__main__":
    main()
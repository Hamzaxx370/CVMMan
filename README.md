# CVMMan
PS2 Yakuza CVM unpacker and repacker

# Usage
# Patching:
- CVMMan -p --game "Y1/Y2_1/Y2_2" --patch-dir "YOUR-MOD-FOLDER" --game-dir "YOUR-GAME-FOLDER"
## Requirements:
- Game folder containing all PS2 game files
- Mod folder containing MEDIA folders
# Extracting:
- CVMMan -u --cvm-file "YOUR-CVM" --dir-file "YOUR-OGREDIR"
# Repacking:
- CVMMan -r --list-file "YOUR-LIST.JSON"
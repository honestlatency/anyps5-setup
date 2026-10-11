# How to Set Up AnyPS5 on Windows (Step by Step)

Companion files for the video: **[How to Run PS5 Games on PC - AnyPS5 Setup](https://www.youtube.com/watch?v=DwF6UpRaTfc)** on [Honest Latency](https://www.youtube.com/@HonestLatency).

Tested on an Intel i5 laptop with Iris Xe graphics and 16 GB RAM, Windows 11, October 2026. The game used is [DOOM for PS5](https://github.com/lowbit/ps5-doom), a free, open-source fan port packaged like a real PS5 game. Nothing here covers dumping games.

## unself.py

[`unself.py`](unself.py) turns a **plaintext (fake-signed) SELF** into the plain ELF the AnyPS5 relinker expects. Homebrew such as DOOM for PS5 ships wrapped like this.

- No decryption. It refuses encrypted or compressed segments, so it does nothing for retail games. For a real game, your dump tool should give you the unwrapped file.
- No dependencies. Python 3 standard library only.

```powershell
py unself.py app0\eboot.bin app0\eboot.bin
py unself.py app0\sce_module\libc.prx app0\sce_module\libc.prx
```

Check the result: the first bytes should read `7F 45 4C 46` (`ELF`).

```powershell
Format-Hex app0\eboot.bin | Select-Object -First 1
```

`4F 15 3D 1D` or `54 14 F5 EE` means it is still a SELF container.

## Every command from the video

**Check your GPU**
```
vulkaninfo | findstr shaderInt64
```
`true` is good. `false` means use lavapipe (below).

**Build AnyPS5** (Command Prompt). Unzip [WinLibs GCC 15.2.0 r7](https://github.com/brechtsanders/winlibs_mingw/releases/tag/15.2.0posix-14.0.0-ucrt-r7) to `C:\winlibs` first.
```bat
pip install cmake ninja
set PATH=C:\winlibs\mingw64\bin;%PATH%
git clone https://github.com/boykopovar/AnyPS5.git
cd AnyPS5
git submodule update --init --recursive
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++
cmake --build build
cmake --build build --target libs
```
If configure fails downloading FFmpeg with an SSL certificate error, run this, then configure again:
```bat
set SSL_CERT_FILE=C:\Program Files\Git\mingw64\etc\ssl\certs\ca-bundle.crt
```

**Game folder** (Command Prompt, inside `C:\Games\DOOM`)
```
DOOM\
  app0\   the whole game, unchanged (eboot.bin, sce_sys\, sce_module\)
  libs\   AnyPS5 .prx files + the 3 DLLs below
```
```bat
copy C:\PS5Setup\AnyPS5\build\core\libs\libs\*.prx libs
copy C:\winlibs\mingw64\bin\libgcc_s_seh-1.dll libs
copy "C:\winlibs\mingw64\bin\libstdc++-6.dll" libs
copy C:\winlibs\mingw64\bin\libwinpthread-1.dll libs
```
Keep the quotes on the libstdc++ line. In `copy`, `+` means "join files".

**Check, convert, audit, run** (PowerShell from here on)
```powershell
Format-Hex app0\eboot.bin | Select-Object -First 1
.\relinker.exe --windows --to-intel --registry app0\eboot.bin eboot.exe
py C:\PS5Setup\AnyPS5\tools\import_audit.py eboot.registry.json eboot.libc.prx.guest.prx.registry.json --libs libs --modules app0\sce_module
.\eboot.exe > run.log 2>&1
```
`--to-intel` is only needed on Intel CPUs. In the audit output, `absent` should be `0`.

**No shaderInt64? Lavapipe** ([Mesa for Windows](https://github.com/pal1000/mesa-dist-win/releases), extracted to `C:\mesa`). This applies to that terminal window only.
```powershell
$env:VK_DRIVER_FILES = "C:\mesa\x64\lvp_icd.x86_64.json"
$env:ANYPS5_GPU = "llvmpipe"
.\eboot.exe
```

## Common errors

| Message | Fix |
|---|---|
| `193` | A Sony `.prx` is in `libs`. Take it out. |
| `126` | Windows can't find a file, usually one of the 3 DLLs. Copy them into `libs`. |
| `create direct memory backing failed` | Page file too small. Make it bigger, or close Chrome. |
| `The input is a SELF container, not an ELF` | Run `unself.py` (homebrew) or use your dump tool's unwrapped file. |
| `buffer device address and shaderInt64 are required` | Your GPU driver lacks shaderInt64. Use lavapipe. |

## Links

- AnyPS5 (the only official place): https://github.com/boykopovar/AnyPS5
- DOOM for PS5: https://github.com/lowbit/ps5-doom
- WinLibs: https://github.com/brechtsanders/winlibs_mingw
- Mesa for Windows: https://github.com/pal1000/mesa-dist-win

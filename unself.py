"""Unwrap a plaintext (fake-signed) PS4/PS5 SELF into the plain ELF AnyPS5 wants.

No decryption: refuses encrypted or compressed segments.
usage: py -I unself.py <in.self> <out.elf>
"""
import struct
import sys

MAGICS = {b"\x4f\x15\x3d\x1d", b"\x54\x14\xf5\xee"}  # PS4-style, PS5
ENC, COMP, BLOCKS = 1 << 1, 1 << 3, 1 << 11


def unself(data: bytes) -> bytes:
    if data[:4] not in MAGICS:
        raise ValueError("not a SELF container")
    n_entries = struct.unpack_from("<H", data, 0x18)[0]
    entries = [struct.unpack_from("<4Q", data, 0x20 + i * 32) for i in range(n_entries)]
    ehdr_off = 0x20 + n_entries * 32
    if data[ehdr_off:ehdr_off + 4] != b"\x7fELF":
        raise ValueError("no ELF header after the SELF entries")
    phoff, = struct.unpack_from("<Q", data, ehdr_off + 0x20)
    phentsize, phnum = struct.unpack_from("<HH", data, ehdr_off + 0x36)
    phdrs = [struct.unpack_from("<IIQQQQQQ", data, ehdr_off + phoff + i * phentsize) for i in range(phnum)]

    end = max([phoff + phnum * phentsize] + [p[2] + p[5] for p in phdrs])
    out = bytearray(end)
    head = phoff + phnum * phentsize
    out[:head] = data[ehdr_off:ehdr_off + head]
    out[0x28:0x30] = bytes(8)                       # e_shoff: section headers are not carried
    out[0x3a:0x40] = bytes(6)                       # e_shentsize, e_shnum, e_shstrndx

    for props, offs, filesz, _memsz in entries:
        if not props & BLOCKS:
            continue                                # digest / meta entry
        if props & (ENC | COMP):
            raise ValueError("segment is encrypted or compressed; this tool only unwraps plaintext FSELFs")
        p = phdrs[(props >> 20) & 0xFFF]
        out[p[2]:p[2] + filesz] = data[offs:offs + filesz]

    for p in phdrs:                                 # PT_SCE_VERSION lives at the end of the SELF
        if p[0] == 0x6FFFFF01 and p[5]:
            out[p[2]:p[2] + p[5]] = data[-p[5]:]
    return bytes(out)


if __name__ == "__main__":
    src, dst = sys.argv[1:3]
    with open(src, "rb") as f:
        elf = unself(f.read())
    with open(dst, "wb") as f:
        f.write(elf)
    print(f"{src} -> {dst}: {len(elf)} bytes")

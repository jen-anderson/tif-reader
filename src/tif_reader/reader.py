import sys #Built in module, access to Cmd line args, exit controls
import struct #Converts raw bytes <=> Python numbers
from typing import Any, Union,BinaryIO

fmt_dict = {
    1: "B",   # BYTE
    2: "c",   # ASCII
    3: "H",   # SHORT
    4: "I",   # LONG
    5: "II",  # RATIONAL
    6: "b",   # SBYTE
    7: "B",   # UNDEFINED
    8: "h",   # SSHORT
    9: "i",   # SLONG
    10:"ii",  # SRATIONAL
    11:"f",  # FLOAT
    12:"d",  # DOUBLE
}

type_sizes = {
    1:1, 2:1, 3:2, 4:4, 5:8,
    6:1, 7:1, 8:2, 9:4, 10:8,
    11:4, 12:8
}

def parse_ifd(file: BinaryIO, endian: str, num_entries: int) -> dict[Union[int, str], Any]:
    tags = {}  # key: tag number, value: parsed data
    last_entry_info = None
    for _ in range(num_entries):
        entry_data = file.read(12)
        tag, field_type, count, value_offset = struct.unpack(endian + "HHII", entry_data)
        

        if field_type not in fmt_dict:
            print(f"Skipping unknown field type {field_type} for tag {tag}")
            continue
        
        size_bytes = type_sizes.get(field_type, 1) * count
        curr_pos = file.tell()
        
        # Decide if value is in offset or directly stored
        if size_bytes <= 4:
            if endian == "<":
                value = value_offset & ((1 << (size_bytes*8)) - 1)
            else:
                value = value_offset >> ((4 - size_bytes)*8)
        else:
            file.seek(value_offset)
            fmt = fmt_dict[field_type] * count
            raw = file.read(size_bytes)
            value = struct.unpack(endian + fmt, raw)
            
            if len(value) == 1:
                value = value[0]
            elif field_type == 2:  # ASCII string
                value = b''.join(value).decode("ascii").rstrip("\x00")
            elif field_type in (5, 10):  # RATIONAL/SRATIONAL
                value = [(value[i], value[i+1]) for i in range(0, len(value), 2)]
            
            file.seek(curr_pos)
        
        tags[tag] = value
        last_entry_info = (tag, field_type,count,value_offset, value)
        
    if last_entry_info:
        tag, field_type, count, value_offset, value = last_entry_info
        print(f"Last entry info: Tag={tag}, Type={field_type}, Count={count}, ValueOffset={value_offset}, Value={value}")
       
    # Extract main image size if available
    width = tags.get(256)
    height = tags.get(257)
    tags["_image_size"] = (width, height)
    
    return tags

def read_tiff_header(path: str) -> dict[Union[int, str], Any]:
    with open(path, "rb") as file: #rb = read binary; with = open and automatically close when done
        header = file.read(8)
        byte_order = header[0:2]#End index exclusive in Python

        if byte_order == b"II":
            endian = "<" #Little endian, 0x002A = 2A 00
        elif byte_order ==b"MM":
            endian = ">" #Big endian, 0x002A= 00 2A  
        else: 
            raise ValueError("Not a valid TIFF file")


        magic_number = struct.unpack(endian + "H", header[2:4])[0]
        if magic_number !=42:
            raise ValueError(f"Invalid TIFF magic number: {magic_number}")
        
        offset = struct.unpack(endian +"I", header[4:8])[0]
        print("Byte order:", byte_order)
        print("Magic number:", magic_number)
        print("IFD offset bytes:", offset)

        file.seek(offset) #Move file cursor
        num_entries = struct.unpack(endian + "H",file.read(2))[0] #Read entry count,H= unsigned short
        print("Number of IFD entries:", num_entries)
        
        return parse_ifd(file, endian, num_entries)
    

  
        

if __name__ == "__main__":
    if len(sys.argv) < 2: #argv is CLI arguments - enough args?
        print ("Usage: python reader.py <file>")
        sys.exit(1)  #Error
    path = sys.argv[1]
    tag_data = read_tiff_header(path)

    print("\nFinal Width/Height:", tag_data.get("_image_size"))        
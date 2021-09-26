# File
tag     : "sbconf01"
pages   : ...
end tag : 0xFF
## For each page : 

start tag : 0x01 0xnn (nn = page number)
icons     : ...
end tag   : 0xFE 

## For each icons :

start tag : 0x02 0xrr 0xcc          (rr = row, cc = column)
bmp len   : 0xaa 0xbb 0xcc 0xdd     (size of the bmp file, 4 bytes, big endian)
bmp data  : ...
end tag   : 0xFD

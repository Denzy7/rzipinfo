import requests
import zlib
import argparse
import os
parser = argparse.ArgumentParser(description="get info and extract remote zip (<4GB or 2^32-1, 32 bit only!) zip files")
parser.add_argument("url", help="url for zip")
parser.add_argument("-e", dest="extract", type=int,
                    help='say which file is extracted and stop when done:' +
                    'python rzipinfo.py -e 9 http://example.com/example.zip: extract 10th file in example.zip.' +
                    'you might have to run first without extract to see file number index')
args = parser.parse_args()

eocdr = b'PK\x05\x06'

print('getting headers...')
response = requests.head(args.url)
length = int(response.headers['Content-Length'])
print('file is ', length, ' bytes')
print('retreiving cdr(22 bytes)...')

# TODO: check if Accept-Ranges is available
# TODO: check eocdr when comment is set

# TODO: zip64? probably never XD
# TODO: multiple disk files? naah too complicated but possible

# https://en.wikipedia.org/wiki/ZIP_(file_format)

response = requests.get(args.url, headers={'Range': 'bytes=' + str(length-22) + '-' + str(length)})
if eocdr != response.content[:4]:
    print('this is probably not a zip file')
    exit(1)
else:
    print('zip check passed')

# extract central directory info
cdrecords = int.from_bytes(response.content[10:12], byteorder='little')
cdsize = int.from_bytes(response.content[12:16], byteorder='little')
cdoffset = int.from_bytes(response.content[16:20], byteorder='little')

print('cdr: records:', cdrecords, ',size:', cdsize, ',offset:', cdoffset)

print('retreiving cdr...')
response = requests.get(args.url, headers={'Range': 'bytes=' + str(cdoffset) + '-' + str(cdoffset + cdsize)})

sz_processed = 0
store = 0
deflate = 8
for i in range(cdrecords):
    comprmeth =  int.from_bytes(response.content[sz_processed + 10 : sz_processed + 12], byteorder='little')
    if comprmeth == store:
        meth = "store"
    elif comprmeth == deflate:
        meth = "deflate"
    else:
        meth = "unknown"
    sz_compr =  int.from_bytes(response.content[sz_processed + 20: sz_processed + 24], byteorder='little')
    sz_uncompr = int.from_bytes(response.content[sz_processed + 24: sz_processed + 28], byteorder='little')
    sz_name = int.from_bytes(response.content[sz_processed + 28: sz_processed + 30], byteorder='little')
    sz_extra = int.from_bytes(response.content[sz_processed + 30: sz_processed + 32], byteorder='little')
    sz_comment = int.from_bytes(response.content[sz_processed + 32: sz_processed + 34], byteorder='little')
    off_lfh = int.from_bytes(response.content[sz_processed + 42: sz_processed + 46], byteorder='little')

    name = response.content[sz_processed + 46: sz_processed + 46 + sz_name].decode("utf-8")
    basename = os.path.basename(name)
    print(i, name,
          "compressed:", sz_compr, "uncompressed:", sz_uncompr,
          "method:", meth, "off:", off_lfh)
    if i == args.extract:
        if meth == "unknown":
            print("file compressed with unknown method :(")
        else:
            lfhr_pad = off_lfh + 30 + sz_name + sz_extra + 4
            bytereq = str(lfhr_pad) + '-' + str(lfhr_pad + sz_compr)
            print("asking server bytes", bytereq)
            comp = requests.get(args.url, headers={'Range': 'bytes=' + bytereq})
            decomp = comp.content
            if comprmeth == deflate:
                decomp = zlib.decompress(comp.content, -15, sz_uncompr)
            with open(basename, "wb") as f:
                f.write(decomp)
                print("saved", basename)
                break

    sz_processed += 46 + sz_name + sz_extra + sz_comment

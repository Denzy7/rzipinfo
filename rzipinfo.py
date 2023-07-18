import requests
import sys

try:
    url = sys.argv[1]
    print('zip url: ', url)
except IndexError:
    print('use argv[1] for zip url like:\npython rzipinfo.py http://example.com/example.zip')
    exit(1)

eocdr = b'PK\x05\x06'

print('getting headers...')
response = requests.head(url)
length = int(response.headers['Content-Length'])
print('file is ', length, ' bytes')
print('retreiving cdr(22 bytes)...')

#TODO: check if Accept-Ranges is available
#TODO: check eocdr when comment is set

#https://en.wikipedia.org/wiki/ZIP_(file_format)

response = requests.get(url, headers={'Range': 'bytes=' + str(length-22) + '-' + str(length)})
if eocdr != response.content[:4]:
    print('this is probably not a zip file')
    exit(1)
else:
    print('zip check passed')

#extract central directory info
cdrecords = int.from_bytes(response.content[10:12], byteorder='little')
cdsize = int.from_bytes(response.content[12:16], byteorder='little')
cdoffset = int.from_bytes(response.content[16:20], byteorder='little')

print('cdr: records=',cdrecords,',size=',cdsize,',offset=',cdoffset)

print('retreiving cdr...')
response = requests.get(url, headers={'Range': 'bytes=' + str(cdoffset) + '-' + str(cdoffset + cdsize)})

sz_processed = 0
for i in range(cdrecords):
    sz_name = int.from_bytes(response.content[sz_processed + 28 : sz_processed + 30], byteorder='little')
    sz_extra = int.from_bytes(response.content[sz_processed + 30 : sz_processed + 32], byteorder='little')
    sz_comment = int.from_bytes(response.content[sz_processed + 32 : sz_processed + 34], byteorder='little')
    name = response.content[sz_processed + 46 : sz_processed + 46 + sz_name]
    print(name.decode('utf-8'))
    sz_processed += 46 + sz_name + sz_extra + sz_comment
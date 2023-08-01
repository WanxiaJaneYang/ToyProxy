'''
1. freshness check:
checked if the cached file is stale by checking "Expires" header when a cache hit happens
if the max-age doesn't appear, check if the file is stale by checking the value of Expires
implementing this by comparing the expires date with current date

2. pre-fetched associated files:
first read the received html string and match the url by regular expression  added them to an array that records all the related files
then after the webpage is cached, begin to cache these related files one by one
for each file,create a new socket, send new request and save the data received according to the url

during implementing this function, I extracted many parts of the code as helper function such as:
    createSocket():returns a socket object
    connectSocket(socketObj, hostname,port):connect a socket using hostname and port
    sendRequest(socketObj,request):send request through a socket
    generateRequest(hostname, source): generate a request(string) by hostname and source
    parseUrl(url):return [hostname, resource, port] by parsing a given url
    generateCachePath(hostname,resource):generate a cache path by hostname and resource
    prepareCacheFile(cachePath):return an opened cache file waiting to be written
    writeToCache(cacheFile, data):write data to a cache file and close the file
    receiveData(socketObj):return the data received through a certain socket
then I wrote two functions to help fectching related files and cache them:
    extractUrl(datalines):read the datalines and return an array of urls. if no url found, return an empty array
    cacheRelatedFiles(url):create a socket object and use given url to fetch data and cache the data. this function is implemented by calling the functions above


3. handle port number:
I implement this function by modifying the parseUrl function. Previously my parseUrl will return an array ([hostname, resource, port]) where port would be set as 80
after modification, if ":" found in the hostname, extract the part after ":" as port number
otherwise use the default port number 80

MAIN function begins at line 227
'''


# Include the libraries for socket and system calls
import socket
import sys
import os
import argparse
import re

# Library to extract and calculate age
import email.utils as eut
import datetime
from pytz import timezone

# 1MB buffer size
BUFFER_SIZE = 1000000

# helper function 1
# return current time based on the timeZone given
def getCurrentTime(timeZone):
    return datetime.datetime.now(timeZone).replace(tzinfo=None)

# helper function 2
# parse date to have the same format as the date returned from getCurrentTime()
def parseDate(date):
    return datetime.datetime(*eut.parsedate(date)[:6])

#function to create an socket object
def createSocket():
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    

#function to connect a socket to a server by hostname and portnumber
def connectSocket(socketObj, hostname, port):
    try:
        hostAddress=socket.gethostbyname(hostname)
        socketObj.connect((hostAddress,port))
        print("successfully connected to "+hostname)
    except IOError as e:
        print(hostname+" connection failed", e)
    
#function of sending request through socket
def sendRequest(socketObj, request):
    try:
        socketObj.sendall(request)
    except socket.error:
        print 'Send failed'
        sys.exit()
    return

#generate request by given hostname and resource address
#returns a string
def generateRequest(method,resource,version, hostname):
    originServerRequestLine = ''
    originServerRequestHeader = ''
    originServerRequestLine =method+' '+resource+ ' '+version
    originServerRequestHeader = 'HOST: ' + hostname
    request=originServerRequestLine + \
        '\r\n' + originServerRequestHeader + '\r\n\r\n'
    return request

#parse hostname and resource through a given url, returns an array[hostname, source, port]
def parseUrl(url):
    parsedUrl=[]
    url = re.sub('^(/?)http(s?)://', '', url, 1)
    url = url.replace('/..', '')
    resourceParts = url.split('/', 1)
    hostname = resourceParts[0]
    resource = '/'
    port=80
    if len(resourceParts) == 2:
        # Resource is absolute URI with hostname and resource
        resource = resource + resourceParts[1]
    #if port number is specified in the url
    if hostname.find(":")!=-1:
        parseHostname=hostname.split(":")
        hostname=parseHostname[0]
        try:
            port=int(parseHostname[1])
        except:
            print("port number parsing error")
    parsedUrl.append(hostname)
    parsedUrl.append(resource)
    parsedUrl.append(port)
    print("parsedUrl:\t", parsedUrl)
    return parsedUrl

#generate cache file path by hostname and resource
def generateCachePath(hostname,resource):
    cachePath = './' + hostname + resource
    if cachePath.endswith('/'):
        cachePath = cachePath + 'default'
    print("cache path generated: ", cachePath)
    return cachePath

#create a open cache file 
def prepareCacheFile(cachePath):
    cacheDir, file = os.path.split(cachePath)
    print('cached directory ' + cacheDir)
    if not os.path.exists(cacheDir):
        os.makedirs(cacheDir)
    try:
        file = open(cachePath, 'wb')
        print("open cache file")
    except:
        print("open cache file failed")
    return file

#write data to cache file and close the file
def writeToCache(data, cacheFile):
    try:
        cacheFile.write(data)
        print("cache file written")
    except:
        print("cache file written failed")
    
    cacheFile.close()
    print('cache file closed')
    return

#function to receive data through a socket
def recieveData(socketObj):
    # use to store response from the origin server
    data = ''

    # Get the response from the origin server
    data_received=False
    while not data_received:
        received = socketObj.recv(BUFFER_SIZE)
        data += received
        data_received=True
        break
    return data

#ADDED FUNCTION
#return an array of urls extracted in received data
def extractURL(dataLines):
    urls=[]
    htmlFile=None
    try:
        #extract html doc first
        for line in dataLines:
            if line.startswith("<html"):
                htmlFile=line
        #regex that matches urls
        href_pattern = re.compile(r'href=[\'"]?([^\'" >]+)')
        src_pattern = re.compile(r'src=[\'"]?([^\'" >]+)')
    
        #search url line by line
        for line in htmlFile.splitlines():
            href_match = re.search(href_pattern, line)
            src_match = re.search(src_pattern, line)
            if href_match:
                url = href_match.group(1)
                #at first I thought we don't cache the related webpage to avoid endless caching, but I'm wrong. Thank you Anonymous student who asked this question in Piazza
                #check if it is a file link
                #if '.' in url.split('/')[-1]:
                urls.append(url)
            if src_match:
                url = src_match.group(1)
                #check if it is a file link
                #if '.' in url.split('/')[-1]:
                urls.append(url)
        #print("extract urls:", urls)
    except:
        print("extract url failed")
    return urls

#ADDED FUNCTION
#cache file by given url
def cacheRelatedFiles(url):
    #create a socket
    fileSocket=createSocket()
    #get hostname and resource by url
    urlInfo=parseUrl(url)
    hostName=urlInfo[0]
    resource=urlInfo[1]
    port=urlInfo[2]
    #connect to the file server
    connectSocket(fileSocket,hostName,port)
    #generate and send request for file
    fileRequest=generateRequest(hostName,resource)
    sendRequest(fileSocket,fileRequest)
    #receive file data and cache it
    fileData=recieveData(fileSocket)
    fileCachePath=generateCachePath(hostName,resource)
    fileCacheFile=prepareCacheFile(fileCachePath)
    writeToCache(fileData,fileCacheFile)
    #shut down the file socket
    fileSocket.shutdown(socket.SHUT_WR)
    print('origin server done sending')
    

###MAIN FUNCTION STARTS
###Main FUNCTION STARTS
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()

# Create a server socket, bind it to a port and start listening
# The server IP is in args.hostname and the port is in args.port
# bind() accepts an integer only
# You can use int(string) to convert a string to an integer
# ~~~~ INSERT CODE ~~~~
# ~~~~ END CODE INSERT ~~~~

try:
    # Create a server socket
    serverSocket = createSocket()    
    print 'Created socket'
except:
    print 'Failed to create socket'
    sys.exit()
    
try:
    # Bind the server socket to a host and port
    serverSocket.bind((args.hostname, int(args.port)))
    print 'Port is bound'
except:
    print 'Port is in use'
    sys.exit()

try:
    # Listen on the server socket
    # ~~~~ INSERT CODE ~~~~
    serverSocket.listen(1)
    # ~~~~ INSERT CODE ~~~~
    print 'Listening to socket'
except:
    print 'Failed to listen'
    sys.exit()

while True:
    print '\n\nWaiting connection...'
    
    try:
        # Accept connection from client and store in the clientSocket
        # ~~~~ INSERT CODE ~~~~
        clientSocket, clientAddress = serverSocket.accept()
        # ~~~~ END CODE INSERT ~~~~
        print 'Received a connection from:', args.hostname
    except:
        print 'Failed to accept connection'
        sys.exit()

    clientRequest = 'METHOD URI VERSION'
    # Get request from client
    # and store it in clientRequest
    # ~~~~ INSERT CODE ~~~~
    clientRequest=clientSocket.recv(BUFFER_SIZE)
    # ~~~~ END CODE INSERT ~~~~

    print 'Received request:'
    print '< ' + clientRequest

    # Extract the parts of the HTTP request line from the given message
    requestParts = clientRequest.split()
    method = requestParts[0]
    URI = requestParts[1]
    version = requestParts[2]

    print 'Method:\t\t' + method
    print 'URI:\t\t' + URI
    print 'Version:\t' + version
    print ''
    print ''

    #get hostname and resource from url
    urlInfo=parseUrl(URI)
    hostname=urlInfo[0]
    resource=urlInfo[1]
    port=urlInfo[2]
    print "hostname:\t"+hostname
    print 'Requested Resource:\t' + resource
    
    #generate a cache path for further use
    cachePath = generateCachePath(hostname,resource)
    print 'Cache location:\t\t' + cachePath

    fileExists = os.path.isfile(cachePath)

    try:
        # Check wether the file exist in the cache
        # read the cache
        cacheFile = open(cachePath, "r")
        cacheData = cacheFile.readlines()

        print 'Cache hit! Loading from cache file: ' + cachePath

        # ProxyServer finds a cache hit
        # handle cache directives in the header field
        # Check if the cache is suitable to re-use (Any "cache-control" header in the cache?)
        # If the cache can be re-use, send back contents of cached file
        # ~~~~ INSERT CODE ~~~~
        reuse = True
        timeStamp=None
        timeLimit=None
        expireDate=None
        maxAgeFound=False
        expiresFound=False
        for line in cacheData:
            #get timeStamp
            if line.startswith("Date"):
                timeStamp=parseDate(line[6:])
            if line.startswith("Cache-Control"):
                #get the time limit from max-age
                if "max-age" in line:
                    maxAgeFound=True
                    parsedInfo=line.split('=')
                    timeLimit=int(parsedInfo[1].strip())
                    timeDiff= getCurrentTime(timezone("UTC"))-timeStamp
                    #if the cache is too old to use
                    if timeDiff.total_seconds()>timeLimit:
                        reuse=False
                        cacheFile.close()
                        os.remove(cachePath)
                        break
                #search for Expires header
            if line.startswith("Expires"):
                expiresFound=True
                #get the expire date
                index=line.find(":")
                expireDate=line[index+1:]
                expireDate=parseDate(expireDate.strip())
                print(expireDate)
                break
            
        #if max-age not appears and expires appears:
        if (not maxAgeFound) and expiresFound:
            if getCurrentTime(timezone("UTC"))>expireDate:
                reuse=False
                cacheFile.close()
                os.remove(cachePath)
                
        if(reuse):
            clientSocket.send(''.join(cacheData))
        else:
            raise IOError("cache file not suitable")
        # ~~~~ END CODE INSERT ~~~~
        cacheFile.close()
        print 'cache file closed'

    # Error handling for file not found in cache and cache is not suitable to send
    except IOError:
        originServerSocket = createSocket()     
        print 'Connecting to:\t\t' + hostname + "\n"
        print ("port:",port)
        try:
            connectSocket(originServerSocket,hostname,port)
            print 'Connected to origin Server'

            # Create a file object associated with this socket
            # This lets us use file function calls
            originServerFileObj = originServerSocket.makefile('+', 0)

            # Construct the request to send to the origin server
            originServerRequest = generateRequest(hostname,resource)

            # Request the web resource from origin server
            print 'Forwarding request to origin server:'
            for line in originServerRequest.split('\r\n'):
                print '> ' + line

            #send the request to origin server
            sendRequest(originServerSocket,originServerRequest)
            print 'Request sent to origin server\n'
            #write the request into the fileObj
            originServerFileObj.write(originServerRequest)
            
            # receive data from originServerSocket
            data = recieveData(originServerSocket)
            # use to determine if this response should be cached?
            isCache = True
            # Get the response code from the response
            dataLines = data.split('\r\n')
            responseCode = dataLines[0]
            # Decide which content should be cached
            # ~~~~ INSERT CODE ~~~~
            #we should not reuse 302 response unless the cache-control tells us to do so
            #as for 301, we may cache it unless the cache-control header says otherwise
            if "302" in responseCode:
                isCache=False
            elif "404" in responseCode:
                isCache=False
                
            for line in dataLines:
                if line.startswith("cache-control"):
                    if "no-cache" in line:
                        isCache=False
                    elif "max-age" in line:
                        isCache=True
            
            #GET URLS FROM DATALINES
            urls=extractURL(dataLines)
            print("extracted urls:",urls)
            
            # ~~~~ END CODE INSERT ~~~~

            # Send the data to the client
            # ~~~~ INSERT CODE ~~~~
            clientSocket.sendall(data)
            # ~~~~ END CODE INSERT ~~~~

            # cache the content if it should be cached
            if isCache:
                #cache webpage
                cacheFile = prepareCacheFile(cachePath)
                writeToCache(data,cacheFile)

                #cache the related files
                for i in range(len(urls)):
                    cacheRelatedFiles(urls[i])
            # finished sending to origin server - shutdown socket writes
            originServerSocket.shutdown(socket.SHUT_WR)

            print('origin server done sending')
            originServerSocket.close()

            clientSocket.shutdown(socket.SHUT_WR)
            print('client socket shutdown for writing')
        except IOError as e:
            print('origin server request failed. ' + e)
    try:
        clientSocket.close()
    except:
        print('Failed to close client socket')
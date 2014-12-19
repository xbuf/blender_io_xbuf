# Communication Overview

The communication is based on the following rules :

* Messages are send like notification or event, no explicit request/response by default (if it is needed, use a correlation id to link request and response).
* Client / Server communication, assymmetric messages support.
* Currently the messages are exchange over tcp.
* Server (eg: game engine) are bind to 127.0.0.1:4242 (default).
* Client is the front-end editor (eg: blender).
* Client should not freeze when server is unavailable.

# Message

| Offset | Size | description |
|-------:|-----:|-------------|
| 0 | 5 | header,  see header for description |
| 5 | defined in header| body, size and format are defined in the header |


## Header

| Offset | Size | Format | description |
|-------:|-----:|--------|-------------|
| 0 | 4 | big-endian int32 | size in bytes of the body |
| 4 | 1 | byte | kind of the body (kind = format + version)|

## Body

In the sub-sections:

* the value in the title is the value of kind to use with this body
* the offset are relative to the body start.

| Kind | Title | Send by | Required |
|-----:|-------|---------|----------|
| 0x00 | Invalid | none | |
| 0x01 | PingPong | client,server | |
| 0x02 | Log Message | server | |
| 0x03 | Ask Screenshot | client | X |
| 0x04 | Raw Screenshot BGRA| server | X |
| 0x05 | MessagePack encoded | client | |
| ... | Unused | . |. |
| 0xF0 | Reserved for future | .|. |
| ... | Reserved for future | .|. |
| 0xFF | Reserved for future | .|. |


Other value for kind, will be used by other **possible** message or extension, like :
* typed message encoded with [Cap’n Proto](http://kentonv.github.io/capnproto/otherlang.html) when it'll be more windows/python friendly
* scene exported via [opengex](http://opengex.org)
* Screenshot shared by mapped file, shared memory (RAM), or gpu (texture cross context)
* compression, video codec to reduce size of the screenshot.
* custom command meta-data, to allow server to expose custom command to client.
* audio ??

### 0x00 : Invalid

Message with king 0x00 are invalid and should be ignore or raise a warning.

### 0x01 : PingPong

Body used to check the communication. When a peer receive 'ping', it should reply 'pong'. This message could be used to test the connexion, to mesure the minimal  roundtrip.

| Offset | Size | Format | description |
|-------:|-----:|--------|-------------|
| 0 | 4 | big-endian int32 | a correlation id use to link request with response|
| 4 | 1 | byte (**0x01** : ping, **0x02**: pong)| the request or the response|


### 0x02 : Log Message

Used by the server to reply, or to send a list of log messages to the client.

| Offset | Size | Format | description |
|-------:|-----:|--------|-------------|
| 0 | 4 | big-endian int32 | correlation id (**0** no correlation id)|
| 4 | 1 | byte | number of log message|
| 5 | 4 | big-endian int32 | size of the text in bytes|
| 9 | 1 | char (**'t'** trace, **'d'** debug, **'c'** config, **'i'** info, **'w'** warning, **'e'** error, **'f'** fatal)| criticity, level|
| 10 | size | UTF-8| text|

repeat the last 3 (size + criticity + text) for every messages in the list.

### 0x03 : Ask Screenshot

| Offset | Size | Format | description |
|-------:|-----:|--------|-------------|
| 0 | 4 | big-endian int32 | width|
| 4 | 4 | big-endian int32 | height|

### 0x04 : Raw Screenshot BGRA

In response to 'Ask Screenshot', the server can send the image in uncompressed BGRA format. The raw image can be loaded to opengl directly.

| Offset | Size | Format | description |
|-------:|-----:|--------|-------------|
| 0 | 4 | big-endian int32 | width|
| 4 | 4 | big-endian int32 | height|
| 8 | width x height x 4 | BGRA8| the raw image with origine (0,0) at bottom left|

### 0x05 : MessagePack encoded

The full body is encoded with [msgpack](http://msgpack.org/), the format is inspired cli or the notification in [msgpack-rpc' spec](https://github.com/msgpack-rpc/msgpack-rpc/blob/master/spec.md).
method.

|Name| Format | description |
|----|--------|-------------|
| method | string | represents the method name |
| args| any[] | the array of the function arguments. The elements of this array is arbitrary object. |

### 0xF0..0xFF : Reserved for future

Reserved to extends the protocol if needed.

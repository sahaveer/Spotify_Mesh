import os
import time
import socket
import struct
import logging
import threading
from typing import Optional, Dict, Any, List
import xml.sax.saxutils as saxutils

import config
import settings
import database
import mesh

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dlna")

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900

_ssdp_socket: Optional[socket.socket] = None
_running = False
_thread: Optional[threading.Thread] = None

def get_device_uuid() -> str:
    my_settings = settings.load_settings()
    return my_settings.get("device_id", "mediahub-upnp-uuid")

def get_desc_xml(base_url: str) -> str:
    my_settings = settings.load_settings()
    device_name = my_settings.get("device_name", "Decentralized Media Hub")
    uuid = get_device_uuid()

    return f"""<?xml version="1.0" encoding="utf-8"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <device>
    <deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>
    <friendlyName>{saxutils.escape(device_name)}</friendlyName>
    <manufacturer>Decentralized Media Hub</manufacturer>
    <manufacturerURL>https://github.com</manufacturerURL>
    <modelDescription>Decentralized Media Hub UPnP/DLNA Server</modelDescription>
    <modelName>MediaHub DLNA</modelName>
    <modelNumber>2.0</modelNumber>
    <modelURL>https://github.com</modelURL>
    <serialNumber>{uuid[:8]}</serialNumber>
    <UDN>uuid:{uuid}</UDN>
    <serviceList>
      <service>
        <serviceType>urn:schemas-upnp-org:service:ContentDirectory:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:ContentDirectory</serviceId>
        <SCPDURL>/dlna/content_directory.xml</SCPDURL>
        <controlURL>/dlna/control</controlURL>
        <eventSubURL>/dlna/events</eventSubURL>
      </service>
      <service>
        <serviceType>urn:schemas-upnp-org:service:ConnectionManager:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:ConnectionManager</serviceId>
        <SCPDURL>/dlna/connection_manager.xml</SCPDURL>
        <controlURL>/dlna/connection_control</controlURL>
        <eventSubURL>/dlna/connection_events</eventSubURL>
      </service>
    </serviceList>
  </device>
</root>"""

def get_content_directory_scpd() -> str:
    return """<?xml version="1.0" encoding="utf-8"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0">
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <actionList>
    <action>
      <name>GetSystemUpdateID</name>
      <argumentList>
        <argument>
          <name>Id</name>
          <direction>out</direction>
          <relatedStateVariable>SystemUpdateID</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
    <action>
      <name>Browse</name>
      <argumentList>
        <argument>
          <name>ObjectID</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_ObjectID</relatedStateVariable>
        </argument>
        <argument>
          <name>BrowseFlag</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_BrowseFlag</relatedStateVariable>
        </argument>
        <argument>
          <name>Filter</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_Filter</relatedStateVariable>
        </argument>
        <argument>
          <name>StartingIndex</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_Index</relatedStateVariable>
        </argument>
        <argument>
          <name>RequestedCount</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_Count</relatedStateVariable>
        </argument>
        <argument>
          <name>SortCriteria</name>
          <direction>in</direction>
          <relatedStateVariable>A_ARG_TYPE_SortCriteria</relatedStateVariable>
        </argument>
        <argument>
          <name>Result</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_Result</relatedStateVariable>
        </argument>
        <argument>
          <name>NumberReturned</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_Count</relatedStateVariable>
        </argument>
        <argument>
          <name>TotalMatches</name>
          <direction>out</direction>
          <relatedStateVariable>A_ARG_TYPE_Count</relatedStateVariable>
        </argument>
        <argument>
          <name>UpdateID</name>
          <direction>out</direction>
          <relatedStateVariable>SystemUpdateID</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
  </actionList>
  <serviceStateTable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_ObjectID</name>
      <dataType>string</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_Result</name>
      <dataType>string</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_BrowseFlag</name>
      <dataType>string</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_Filter</name>
      <dataType>string</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_SortCriteria</name>
      <dataType>string</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_Index</name>
      <dataType>ui4</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
      <name>A_ARG_TYPE_Count</name>
      <dataType>ui4</dataType>
    </stateVariable>
    <stateVariable sendEvents="yes">
      <name>SystemUpdateID</name>
      <dataType>ui4</dataType>
    </stateVariable>
  </serviceStateTable>
</scpd>"""

def get_connection_manager_scpd() -> str:
    return """<?xml version="1.0" encoding="utf-8"?>
<scpd xmlns="urn:schemas-upnp-org:service-1-0">
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <actionList>
    <action>
      <name>GetProtocolInfo</name>
      <argumentList>
        <argument>
          <name>Source</name>
          <direction>out</direction>
          <relatedStateVariable>SourceProtocolInfo</relatedStateVariable>
        </argument>
        <argument>
          <name>Sink</name>
          <direction>out</direction>
          <relatedStateVariable>SinkProtocolInfo</relatedStateVariable>
        </argument>
      </argumentList>
    </action>
  </actionList>
  <serviceStateTable>
    <stateVariable sendEvents="yes">
      <name>SourceProtocolInfo</name>
      <dataType>string</dataType>
    </stateVariable>
    <stateVariable sendEvents="yes">
      <name>SinkProtocolInfo</name>
      <dataType>string</dataType>
    </stateVariable>
  </serviceStateTable>
</scpd>"""

def build_didl_browse(object_id: str, base_url: str, starting_index: int = 0, requested_count: int = 100) -> tuple:
    """
    Returns (didl_xml, number_returned, total_matches) for UPnP ContentDirectory Browse action.
    Root containers:
      - '0': Root (Contains Music 'music_root', Videos 'video_root', Photos 'photo_root')
      - 'music_root': All music tracks
      - 'video_root': All movies and videos
      - 'photo_root': All photos
    """
    items = []
    total = 0

    if object_id == "0":
        # Root containers
        containers = [
            ("music_root", "0", "Music", "object.container.storageFolder"),
            ("video_root", "0", "Movies & Videos", "object.container.storageFolder"),
            ("photo_root", "0", "Photos", "object.container.storageFolder")
        ]
        total = len(containers)
        for cid, pid, title, cclass in containers[starting_index:starting_index + requested_count]:
            items.append(f'<container id="{cid}" parentID="{pid}" restricted="1"><dc:title>{saxutils.escape(title)}</dc:title><upnp:class>{cclass}</upnp:class></container>')

    elif object_id == "music_root":
        songs = database.get_songs(media_type="audio", limit=requested_count, offset=starting_index)
        stats = database.get_stats()
        total = stats.get("total_songs", len(songs))
        for s in songs:
            mid = s["id"]
            title = saxutils.escape(s.get("title") or "Unknown Title")
            artist = saxutils.escape(s.get("artist") or "Unknown Artist")
            album = saxutils.escape(s.get("album") or "Unknown Album")
            mime = s.get("mime_type", "audio/mpeg")
            stream_url = f"{base_url}/api/stream/{mid}"
            duration = int(s.get("duration") or 0)
            hours, rem = divmod(duration, 3600)
            mins, secs = divmod(rem, 60)
            dur_str = f"{hours:02}:{mins:02}:{secs:02}"
            items.append(
                f'<item id="{mid}" parentID="music_root" restricted="1">'
                f'<dc:title>{title}</dc:title>'
                f'<upnp:class>object.item.audioItem.musicTrack</upnp:class>'
                f'<dc:creator>{artist}</dc:creator>'
                f'<upnp:artist>{artist}</upnp:artist>'
                f'<upnp:album>{album}</upnp:album>'
                f'<res protocolInfo="http-get:*:{mime}:*" duration="{dur_str}">{stream_url}</res>'
                f'</item>'
            )

    elif object_id == "video_root":
        videos = database.get_videos(limit=requested_count, offset=starting_index)
        stats = database.get_stats()
        total = stats.get("total_videos", len(videos))
        for v in videos:
            vid = v["id"]
            title = saxutils.escape(v.get("title") or "Unknown Video")
            mime = v.get("mime_type", "video/mp4")
            stream_url = f"{base_url}/api/stream/{vid}"
            duration = int(v.get("duration") or 0)
            hours, rem = divmod(duration, 3600)
            mins, secs = divmod(rem, 60)
            dur_str = f"{hours:02}:{mins:02}:{secs:02}"
            items.append(
                f'<item id="{vid}" parentID="video_root" restricted="1">'
                f'<dc:title>{title}</dc:title>'
                f'<upnp:class>object.item.videoItem.movie</upnp:class>'
                f'<res protocolInfo="http-get:*:{mime}:*" duration="{dur_str}">{stream_url}</res>'
                f'</item>'
            )

    elif object_id == "photo_root":
        photos = database.get_photos(limit=requested_count, offset=starting_index)
        stats = database.get_stats()
        total = stats.get("total_photos", len(photos))
        for p in photos:
            pid = p["id"]
            title = saxutils.escape(p.get("title") or "Photo")
            mime = p.get("mime_type", "image/jpeg")
            photo_url = f"{base_url}/api/photo/{pid}/raw"
            items.append(
                f'<item id="{pid}" parentID="photo_root" restricted="1">'
                f'<dc:title>{title}</dc:title>'
                f'<upnp:class>object.item.imageItem.photo</upnp:class>'
                f'<res protocolInfo="http-get:*:{mime}:*">{photo_url}</res>'
                f'</item>'
            )

    didl = (
        '<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">'
        + "".join(items)
        + '</DIDL-Lite>'
    )
    return didl, len(items), total

def _ssdp_loop(port: int):
    global _running, _ssdp_socket
    local_ip = mesh.get_local_ip()
    base_url = f"http://{local_ip}:{port}"
    desc_url = f"{base_url}/dlna/desc.xml"
    uuid = get_device_uuid()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Join multicast group
        mreq = struct.pack("4sl", socket.inet_aton(SSDP_ADDR), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.bind(("", SSDP_PORT))
        sock.settimeout(2.0)
        _ssdp_socket = sock
    except Exception as e:
        logger.warning(f"Could not bind DLNA SSDP socket to port {SSDP_PORT}: {e}")
        return

    logger.info(f"UPnP/DLNA discovery responder active at {desc_url}")

    while _running:
        try:
            data, addr = sock.recvfrom(2048)
            msg = data.decode("utf-8", errors="ignore")
            if "M-SEARCH" in msg and "ssdp:discover" in msg.lower():
                # Check target
                targets = [
                    "ssdp:all",
                    "upnp:rootdevice",
                    "urn:schemas-upnp-org:device:MediaServer:1",
                    "urn:schemas-upnp-org:service:ContentDirectory:1",
                    f"uuid:{uuid}"
                ]
                for target in targets:
                    if target in msg or "ssdp:all" in msg:
                        resp = (
                            "HTTP/1.1 200 OK\r\n"
                            "CACHE-CONTROL: max-age=1800\r\n"
                            f"DATE: {time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())}\r\n"
                            "EXT:\r\n"
                            f"LOCATION: {desc_url}\r\n"
                            "SERVER: Windows/10 UPnP/1.0 MediaPlayer/2.0\r\n"
                            f"ST: {target}\r\n"
                            f"USN: uuid:{uuid}::{target}\r\n"
                            "\r\n"
                        )
                        sock.sendto(resp.encode("utf-8"), addr)
        except socket.timeout:
            continue
        except Exception:
            if not _running:
                break

    try:
        sock.close()
    except Exception:
        pass

def start_dlna_service(port: int = config.PORT):
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_ssdp_loop, args=(port,), daemon=True)
    _thread.start()

def stop_dlna_service():
    global _running
    _running = False

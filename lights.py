import os
import socket
import struct
import time
from threading import Thread, Event
from enum import Enum

# https://github.com/Cryptkeeper/fseq-file-format

FSEQ_HEADER_SIZE = 32
DDP_PORT = 4048
DDP_HEADER_SIZE = 10
DDP_MAX_DATA = 1440  # safe UDP payload size


class State( Enum ):
  PAUSED = 1
  RUNNING = 2

# 40 FPS (step time 50) is 100 bpm


class LightCtrl():
  def __init__( self, fseq_filename, ddp_ip ):
    self.file = open( fseq_filename, 'rb' )
    self.state = State.PAUSED

    header = self.file.read( FSEQ_HEADER_SIZE )
    if header[0:4] != b'PSEQ':
      raise ValueError( 'Not a FSEQ file' )
    (
        self.data_start_pos,
        minor_version,
        major_version,
        header_size,
        self.channel_count,
        self.frame_count,
        self.step_time_ms,
        _,
        compression_info,
        num_compression_blocks,
        sparse_range_count,
        _,
        _,
    ) = struct.unpack_from( '<HBBHIIBBBBBBQ', header, 4 )

    print( f'FSEQ file "{ fseq_filename }" v{ major_version }.{ minor_version }' )
    print( f'  Chanel Count: { self.channel_count }' )
    print( f'  Frame Count: { self.frame_count }' )
    print( f'  Step Time: { self.step_time_ms } (FPS:{ 1000 / self.step_time_ms })' )
    print( f'  Channel Data Offset: { self.data_start_pos }' )
    print( f'  Header Size: { header_size }' )

    if major_version != 2:
      raise ValueError( 'FSEQ file must be version 2.0' )
    if compression_info != 0:
      raise ValueError( 'FSEQ file must uncompressed' )
    if sparse_range_count != 0:
      raise ValueError( 'FSEQ file must not be sparse' )
    if header_size != FSEQ_HEADER_SIZE:
      raise ValueError( f'FSEQ header must be {FSEQ_HEADER_SIZE}' )

    self.file.seek( 0, os.SEEK_END )
    file_size = self.file.tell()

    self.stop_pos = self.data_start_pos + ( self.channel_count * self.frame_count )
    # stop at this number \|/  after that seems to be garbage
    # in theory self.data_start_pos + ( self.channel_count * self.frame_count ) should equal file_size
    # but for some reason the files seem to be padded with other stuff
    if self.stop_pos > file_size:
      raise ValueError( 'FSEQ file size is to small' )

    self.step_time_s = self.step_time_ms / 1000

    self.sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
    self.addr = ( ddp_ip, DDP_PORT )

    self.skew = 0
    self.stop_event = Event()
    self.worker = None
    self.event_callback = lambda key: None

    self.jump_to( 0 )

  def set_event_callback( self, event_callback ):
    self.event_callback = event_callback

  def start( self ):
    def _run():
      print( 'Started Light Thread' )
      sleep_to = time.time() + self.step_time_s
      sequence = 0
      while not self.stop_event.is_set():
        sleep_to += self.step_time_s + self.skew

        if self.state == State.RUNNING and self.file.tell() >= self.stop_pos:
            self.state = State.PAUSED  # need to pass this to state some how

        if self.state == State.RUNNING:
          frame = self.file.read( self.channel_count )
          if frame[0] != 0:
            self.event_callback( frame[0], frame[1] )
          self.send_ddp_frame( frame[ 2: ], sequence )
          sequence += 1

        time.sleep( sleep_to - time.time() )

    self.worker = Thread( target=_run )
    self.worker.start()

  def play( self ):
    self.state = State.RUNNING

  def pause( self ):
    self.state = State.PAUSED

  def stop( self ):
    self.stop_event.set()
    if self.worker:
      self.worker.join()

    self.sock.close()

  def scan_for_commands( self, callback ):  # callback should accept ( command, data, pos in ms )
    self.jump_to( 0 )
    while ( self.file.tell() < self.stop_pos ):
      cur_pos = self.file.tell()
      frame = self.file.read( self.channel_count )
      if frame[0] != 0:
        callback( frame[0], frame[1], cur_pos - self.data_start_pos )

    self.jump_to( 0 )

  def get_pos( self ):
    return ( self.file.tell() - self.data_start_pos ) / self.step_time_ms

  def jump_to( self, pos ):  # pos in ms
    print( f'Jump to {pos}' )
    self.file.seek( self.data_start_pos + pos )

  def send_ddp_frame( self, frame, sequence ):
    offset = 0
    packet_sequence = sequence & 0x0F

    while offset < len( frame ):
      chunk = frame[ offset:offset + DDP_MAX_DATA ]

      flags = 0x40  # push flag
      if offset == 0:
        flags |= 0x01  # start of frame

      if offset + len( chunk ) >= len( frame ):
        flags |= 0x02  # end of frame

      header = struct.pack(
          '!BBBBIH',
          0x41,               # DDP version
          flags,
          packet_sequence,
          0x00,               # data type (RGB)
          offset,
          len( chunk )
      )

      self.sock.sendto( header + chunk, self.addr )
      offset += len( chunk )

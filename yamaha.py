import socket


class YamahaTF:
  def __init__( self, host ):
    self.socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
    self.socket.settimeout( 5 )
    self.socket.connect( host, 49280 )

  def stop( self ):
    self.sock.close()

  def _send( self, command ):
    command += '\n'
    self.sock.sendall( command.encode( 'utf-8' ) )
    return self.sock.recv( 1024 ).decode()

  def set_mono_fader_level( self, channel, db, mix=0 ):
    return self._send( f'set MIXER:Current/InCh/Fader/Level {channel} {mix} {db}' )

  def set_stereo_fader_level( self, channel, db, mix=0 ):
    return self._send( f'set MIXER:Current/StCh/Fader/Level {channel} {mix} {db}' )

  def set_mute( self, channel, mute ):
    value = 1 if mute else 0
    return self._send( f'set MICER:Current/InCh/Fader/On {channel} 0 {value}' )
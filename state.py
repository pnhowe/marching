import time
from datetime import datetime
from enum import Enum

from threading import Thread, Event

from lights import State as LightState
from streamdeck import Icons

FASTER_SLOWER_CHANGE = 5

NUM_KEYS = 15
PLAY_PAUSE_KEY = 0
BPM_KEY = 1
POS_KEY = 2
CUR_MOVEMENT_KEY = 3
CUR_MEASURE_KEY = 4
TAP_START_KEY = 5
SLOWER_KEY = 7
FASTER_KEY = 8
RESET_KEY = 10
EXIT_KEY = 14

class Command( Enum ):
  NOP = 0
  SET_MOVEMENT = 10
  SET_MEASURE = 11
  PAUSE = 20
  BOOKMARK = 22
  JUMP_NOT_READY = 24


class State:
  def __init__( self, light_control, stream_deck ):
    self.cur_movement = 0
    self.light_control = light_control
    self.stream_deck = stream_deck
    self.worker = None
    self.bookmarks = {}
    self.stop_event = Event()

    self.key_callbacks = [ lambda x: None ] * NUM_KEYS
    self.key_contence = [ Icons.EMPTY ] * NUM_KEYS

    self.key_contence[ PLAY_PAUSE_KEY ] = Icons.PLAY
    self.key_contence[ EXIT_KEY ] = Icons.EXIT
    self.key_contence[ RESET_KEY ] = Icons.RESET
    self.key_contence[ POS_KEY ] = 'Pos'
    self.key_contence[ TAP_START_KEY ] = 'Tap Start'
    self.key_contence[ CUR_MOVEMENT_KEY ] = 'Movement'
    self.key_contence[ CUR_MEASURE_KEY ] = 'Measure'
    self.key_contence[ SLOWER_KEY ] = 'Slower'
    self.key_contence[ FASTER_KEY ] = 'Faster'

    self.render()

    self.key_callbacks[ PLAY_PAUSE_KEY ] = self.do_play_pause
    self.key_callbacks[ RESET_KEY ] = self.do_reset
    self.key_callbacks[ EXIT_KEY ] = self.exit
    self.key_callbacks[ CUR_MOVEMENT_KEY ] = self.select_movement
    self.key_callbacks[ CUR_MEASURE_KEY ] = self.select_measure
    self.key_callbacks[ TAP_START_KEY ] = self.tap_start
    self.key_callbacks[ SLOWER_KEY ] = self.slower
    self.key_callbacks[ FASTER_KEY ] = self.faster

    self.load_bookmarks()

    self.screen_state_stack = []

    self.set_bpm( 100 )

  def load_bookmarks( self ):
    current_movement = None
    def callback( command, data, pos ):
      nonlocal current_movement
      if command == Command.SET_MOVEMENT.value:
        current_movement = data
        self.bookmarks[ current_movement ] = { 'pos': pos, 'measures': {} }
        return

      if command == Command.SET_MEASURE.value:
        self.bookmarks[ current_movement ][ 'measures' ][ data ] = pos
        return

    self.light_control.scan_for_commands( callback )
    print( self.bookmarks )

  def set_key_contence( self, key, value, is_root=False ):
    if is_root and self.screen_state_stack:
      self.screen_state_stack[0][1][ key ] = value
      return

    self.key_contence[ key ] = value
    self.stream_deck.set_key( key, value )

  def render( self ):
    for key in range( 0, NUM_KEYS ):
      self.stream_deck.set_key( key, self.key_contence[ key ] )

  def store_screen( self ):
    self.screen_state_stack.append( ( self.key_callbacks, self.key_contence ) )
    self.key_callbacks = [ lambda x: None ] * NUM_KEYS
    self.key_contence = [ Icons.EMPTY ] * NUM_KEYS

  def recall_screen( self ):
    self.key_callbacks, self.key_contence = self.screen_state_stack.pop()

  def run( self ):
    def _run():
      print( 'Started State Thread' )
      while not self.stop_event.is_set():
        time.sleep( 1 )
        self.set_key_contence( POS_KEY, f'{self.light_control.get_pos()}', True )

    self.light_control.jump_to( 0 )
    self.light_control.pause()

    self.worker = Thread( target=_run )
    self.worker.start()
    self.worker.join()

  def key_press( self, key ):
    try:
      handler = self.key_callbacks[ key ]
    except IndexError:
      return
    except Exception as e:
      self.stop_event.set()
      raise e

    handler( key )

  def exit( self, key ):
    self.stop_event.set()

  def handle_event( self, command, data ):
    if command == Command.SET_MOVEMENT.value:
      self.cur_movement = data
      return self.set_key_contence( CUR_MOVEMENT_KEY, f'Movement\n{data}', True )

    if command == Command.SET_MEASURE.value:
      return self.set_key_contence( CUR_MEASURE_KEY, f'Measure\n{data}', True )

    print( f'Unknown Command {command}')

  def do_reset( self, key ):
    self.light_control.jump_to( 0 )

  def do_play_pause( self, key ):
    if self.light_control.state == LightState.RUNNING:
      self.light_control.pause()
      self.set_key_contence( key, Icons.PLAY )

    elif self.light_control.state == LightState.PAUSED:
      self.light_control.play()
      self.set_key_contence( key, Icons.PAUSE )

  def select_movement( self, key ):
    self.store_screen()
    self.key_contence[ EXIT_KEY ] = Icons.BACK
    self.key_callbacks[ EXIT_KEY ] = self.back
    key = 0
    for movement in self.bookmarks.keys():
      self.key_contence[ key ] = f'{movement}'
      self.key_callbacks[ key ] = lambda x, m=movement: self.do_set_movement( m )
      key += 1
    self.render()

  def do_set_movement( self, movement ):
    self.recall_screen()
    self.render()
    self.cur_movement = movement
    self.light_control.jump_to( self.bookmarks[ movement ][ 'pos' ] )

  def select_measure( self, key ):
    self.store_screen()
    self.key_contence[ EXIT_KEY ] = Icons.BACK
    self.key_callbacks[ EXIT_KEY ] = self.back
    key = 0
    for measure in self.bookmarks[ self.cur_movement ][ 'measures' ].keys():
      self.key_contence[ key ] = f'{measure}'
      self.key_callbacks[ key ] = lambda x, m=measure: self.do_set_measure( m )
      key += 1
    self.render()

  def do_set_measure( self, measure ):
    self.recall_screen()
    self.render()
    self.light_control.jump_to( self.bookmarks[ self.cur_movement ][ 'measures' ][ measure ] )

  def tap_start( self, key ):
    self.store_screen()
    self.tap_countdown = 4
    self.tap_timestamp = None
    self.key_contence[ EXIT_KEY ] = Icons.BACK
    self.key_callbacks[ EXIT_KEY ] = self.back

    self.key_contence[ BPM_KEY ] = '100'

    self.key_contence[ TAP_START_KEY ] = f'{ self.tap_countdown }'
    self.key_callbacks[ TAP_START_KEY ] = self.do_tap
    self.render()

  def do_tap( self, key ):
    if self.tap_countdown == 1:
      self.recall_screen()
      elapsed = datetime.now() - self.tap_timestamp
      self.set_bpm( int( 60 / ( ( elapsed.seconds + elapsed.microseconds / 1000000 ) / 4 ) ) )
      self.light_control.play()
      self.set_key_contence( PLAY_PAUSE_KEY, Icons.PAUSE )
      self.render()
      return

    if self.tap_countdown == 4:
      self.tap_timestamp = datetime.now()
    self.tap_countdown -= 1
    self.key_contence[ TAP_START_KEY ] = f'{ self.tap_countdown }'
    self.render()

  def set_bpm( self, bpm ):
    if bpm < 40 or bpm > 300:
      return

    self.bpm = bpm
    self.light_control.skew = ( ( ( self.light_control.step_time_ms * 100 ) / bpm ) - 50 ) / 1000
    self.key_contence[ BPM_KEY ] = f'BPM\n{ bpm }'
    self.render()

  def slower( self, key ):
    self.set_bpm( self.bpm - FASTER_SLOWER_CHANGE )

  def faster( self, key ):
    self.set_bpm( self.bpm + FASTER_SLOWER_CHANGE )

  def back( self, key ):
    self.recall_screen()
    self.render()

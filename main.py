from lights import LightCtrl
from streamdeck import StreamDeck
from state import State
from mixer import MixerCtrl
from api import API


def main():
  stream_deck = None
  light_control = None
  mixer_control = None
  api = None

  print( 'Setting up Light Controller...' )
  light_control = LightCtrl( 'sequence.fseq', '192.168.13.92' )
  print( 'Setting up Mixer Controller...' )
  mixer_control = MixerCtrl( light_control.stop_pos )
  mixer_control.loadPlan( 'plan.json' )
  try:
    print( 'Setting up Stream Deck...' )
    stream_deck = StreamDeck()

    print( 'Setting up State Manager...' )
    state = State( light_control, stream_deck )
    stream_deck.set_keypress_callback( state.key_press )
    light_control.set_event_callback( state.handle_event )

    print( 'Setting up API...' )
    api = API( state, mixer_control )
    api.start()

    print( 'Starting Lights...' )
    light_control.start()

    print( 'Running...' )
    state.run()

  finally:
    print( 'Stopping...' )
    if stream_deck:
      stream_deck.stop()

    if light_control:
      light_control.stop()

    if api:
      api.stop()

  print( 'Done!' )


if __name__ == '__main__':
   main()

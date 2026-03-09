import io
from enum import Enum

from PIL import Image, ImageFont, ImageDraw
from StreamDeck.DeviceManager import DeviceManager

KEY_SIZE = (72, 72)

# image for empty
img_empty = Image.new('RGB', KEY_SIZE, color='black')

# image for exit
img_exit = Image.new('RGB', KEY_SIZE, color='black')
icon = Image.open('images/exit.png' ).resize( (64, 64) )
img_exit.paste( icon, (4, 4), icon )

# image for reset
img_reset = Image.new('RGB', KEY_SIZE, color='black')
icon = Image.open('images/reset.png' ).resize( (64, 64) )
img_reset.paste( icon, (4, 4), icon )

# image for play
img_play = Image.new('RGB', KEY_SIZE, color='black')
icon = Image.open('images/play.png' ).resize( (64, 64) )
img_play.paste( icon, (4, 4), icon )

# image for pause
img_pause = Image.new('RGB', KEY_SIZE, color='black')
icon = Image.open('images/pause.png' ).resize( (64, 64) )
img_pause.paste( icon, (4, 4), icon )

# image for back
img_back = Image.new('RGB', KEY_SIZE, color='black')
icon = Image.open('images/back.png' ).resize( (64, 64) )
img_back.paste( icon, (4, 4), icon )



class Icons( Enum ):
  EMPTY = img_empty
  EXIT = img_exit
  RESET = img_reset
  PLAY = img_play
  PAUSE = img_pause
  BACK = img_back


class StreamDeck():
  def __init__( self ):
    # this is for the ubunt 0.9.1 version of the library, hopfully upstream get's the newer version
    DeviceManager.USB_PID_STREAMDECK_ORIGINAL = 0x00a5
    streamdecks = DeviceManager().enumerate()
    if not streamdecks:
      raise Exception( 'No Stream Decks found!' )

    self.deck = streamdecks[0]

    if self.deck.DECK_TYPE != 'Stream Deck Original':
      raise ValueError( 'Incompatiable Stream Deck!' )

    self.key_press_callback = lambda key: None

    self.deck.open()
    self.deck.reset()

    self.deck.set_key_callback( self._key_change_callback )

  def _key_change_callback( self, _, key, key_state ):
    if not key_state:
      return

    self.key_press_callback( key )

  def set_keypress_callback( self, callback ):
    self.key_press_callback = callback

  def set_image( self, key, img ):
    tmp = img.transpose( Image.FLIP_TOP_BOTTOM ).transpose( Image.FLIP_LEFT_RIGHT )

    img_byte_arr = io.BytesIO()
    tmp.save( img_byte_arr, format='JPEG' )
    img_bytes = img_byte_arr.getvalue()

    self.deck.set_key_image( key, img_bytes )

  def set_icon( self, key, icon ):
    self.set_image( key, icon.value )

  def set_text( self, key, text ):
    img = Image.new( 'RGB', KEY_SIZE, 'black' )
    draw = ImageDraw.Draw( img )
    font = ImageFont.truetype( 'Roboto-Regular.ttf', 14 )
    draw.text( ( img.width / 2, img.height / 2 ), text=text, font=font, anchor='ms', fill='white', align='center' )
    self.set_image( key, img )

  def set_key( self, key, value ):
    if isinstance( value, Icons ):
      return self.set_icon( key, value )

    if isinstance( value, str ):
      return self.set_text( key, value )

    raise ValueError( f'Unknown key type { type( value ) }')

  def stop( self ):
    self.deck.reset()
    self.deck.close()

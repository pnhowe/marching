import json
import math


RESOLUTION = 100  # how many "postion" of the fseq per step in the plan


def interpolate( y1, y2, x1, x2, offset ):
  dx = x2 - x1
  dy = y2 - y1
  return int( y1 + ( ( offset - x1 ) * dy ) / dx )


class MixerCtrl():
  def __init__( self, maxPos ):
    self.numTicks = math.ceil( maxPos / RESOLUTION )
    self.absolute = []
    self.event = []
    self.name = []
    self.path = []

  def loadPlan( self, filename ):
    plan = json.loads( open( filename, 'rb' ).read() )

    for name, data in plan.items():
      print( name, data )
      absolute_list = [ 0 ] * self.numTicks
      event_list = [ None ] * self.numTicks
      self.name.append( name )
      self.path.append( data[ 'path' ] )

      curTick = 0
      curValue = 0
      for nextTick, nextValue in data[ 'timeline' ].items():
        nextTick = int( nextTick )
        if nextTick > self.numTicks or nextTick < 0 or nextTick < curTick:
          continue

        for tick in range( curTick, nextTick ):
          absolute_list[ tick ] = curValue

        if curValue != nextValue:
          for tick in range( curTick, nextTick ):
            event_list[ tick ] = interpolate( curValue, nextValue, curTick, nextTick, tick )
            absolute_list[ tick ] = event_list[ tick ]

        curValue = nextValue
        curTick = nextTick

      for tick in range( curTick, self.numTicks ):
        absolute_list[ tick ] = curValue

      self.absolute.append( absolute_list )
      self.event.append( event_list )

  def writePlan( self, filename ):
    result = {}
    for i in range( 0, len( self.name ) ):
      timeline = {}
      result[ self.name[ i ] ] = { 'path': self.path[ i ], 'timeline': timeline }

    open( filename, 'rb' ).write( json.dumps( result ) )

  def getValue( self, path, tick ):
    pass

  def setValue( self, path, tick, value ):
    pass

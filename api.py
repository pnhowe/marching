from flask import Flask, request
from flask.views import MethodView
from multiprocessing import Process


class MixerView( MethodView ):
  init_every_request = False

  def __init__( self, mixer ):
    self.mixer = mixer

  def get( self ):
    return f"<h1 style='color:orange'>{request.args}</h1>"

  def post( self ):
    return request.json


class StateView( MethodView ):
  init_every_request = False

  def __init__( self, state ):
    self.state = state

  def get( self ):
    return f"<h1 style='color:red'>{request.args}</h1>"

  def post( self ):
    return request.json


class API():
  def __init__( self, state, mixer ):
    self.app = Flask( 'controller' )
    self.worker = None

    self.app.add_url_rule( '/', view_func=self.index )
    self.app.add_url_rule( '/mixer/', view_func=MixerView.as_view( 'da_mixer', mixer ) )
    self.app.add_url_rule( '/state/', view_func=StateView.as_view( 'da_state', state ) )

  def index( self ):
    return "<h1 style='color:blue'>Hello There!</h1>"

  def start( self ):
    def _run():
      self.app.run( host='0.0.0.0' )

    self.worker = Process( target=_run )
    self.worker.start()

  def stop( self ):
    if not self.worker:
      return
    self.worker.terminate()

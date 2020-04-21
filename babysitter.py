#!/usr/bin/python3

from control import Control
from flask import Response
from flask import Flask
from flask import render_template

useFlaskReloader = False
app = Flask(__name__)
control = Control(useFlaskReloader)

@app.route("/")
def index():
	return render_template("index.html")

@app.route("/video_feed")
def video_feed():
	return Response(control.GenerateMultiJPEG(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/getmotions")
def GetMotions():
	title = "Online"
	return render_template("motions.html"
		, title = control.GetTitle()
		, recording = control.IsRecording()
		, watching = control.IsWatching()
		, motions = control.GetMotions()
		, lastMove = control.GetLastMove()
		, lastDuration = control.GetLastDuration())

@app.route("/play/<motion>")
def Play(motion):
	control.Play(motion)
	return (control.GetTitle(), 204)

@app.route("/del/play/<motion>")
def Delete(motion):
	control.Delete(motion)
	return (control.GetTitle(), 204)

@app.route("/now")
def PlayNow():
	control.PlayNow()
	return (control.GetTitle(), 204)

@app.route("/stop")
def Stop():
	control.Stop()
	return (control.GetTitle(), 204)

@app.route("/rec")
def Record():
	control.Record()
	return (control.GetTitle(), 204)

@app.route("/watch")
def ToggleWatch():
	control.ToggleWatch()
	return (control.GetTitle(), 204)


if __name__ == '__main__':
	app.run(host='0.0.0.0', port='5000', debug=True,
		threaded=not useFlaskReloader, use_reloader=useFlaskReloader)
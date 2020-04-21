from motionDetector import MotionDetector
from imutils.video import VideoStream
import time
import datetime
import os
from enum import Enum

class E_State(Enum):
	stopped = 0
	camera = 1
	recording = 2
	history = 3

class Control:
	def __init__(self, useFlaskReloader):
		self.md = MotionDetector(oneFrame=useFlaskReloader)
		self.title = ""
		self.videosDir = "./videos/"
		self.state = E_State.stopped
		self.playing = ""
		self.PlayNow()
		self.watching = False

	def GetTitle(self):
		return self.title

	def GetLastMove(self):
		return self.md.GetLastMove()

	def GetLastDuration(self):
		return self.md.GetLastDuration()

	def IsRecording(self):
		return self.__IsState(E_State.recording)

	def GetMotions(self):
		videos = []
		for r, dirs, files in os.walk(self.videosDir):
			for file in files:
				if '.avi' in file and len(file) == 21:
					vp = file.strip('.avi').split('_')
					if len(vp) == 6:
						videoTime = vp[0] + '.' + vp[1] + '.' + vp[2] + ' ' + vp[3] + ':' + vp[4] + ':' + vp[5]
						size = int(round(os.path.getsize(r + file) / 1024))
						videos.append((videoTime, str(size) + 'kB', "/play/" + file))
		return videos

	def GenerateMultiJPEG(self):
		return self.md.GenerateMultiJPEG()

	def Play(self, motion):
		self.__SetState(E_State.history)
		self.title = "Playing: " + motion
		self.playing = motion
		if not self.md.PlayFile(self.videosDir + motion):
			self.PlayNow()

	def PlayNow(self):
		self.__SetState(E_State.camera)
		self.title = "Camera"
		self.playing = "Camera"
		self.md.PlayCamera()

	def Delete(self, motion):
		if self.playing == motion:
			self.Stop()
		os.remove(self.videosDir + motion)

	def Stop(self):
		self.__SetState(E_State.stopped)
		self.title = "Stopped"
		self.playing = ""
		self.md.Stop()

	def Record(self):
		wasRec = self.__IsState(E_State.recording)
		self.PlayNow()
		if not wasRec:
			timestamp = datetime.datetime.now()
			filename = timestamp.strftime("%d_%m_%y_%H_%M_%S.avi")
			if self.md.StartRecording(self.videosDir + filename):
				self.title = "Recording"
				self.__SetState(E_State.recording)

	def ToggleWatch(self):
		self.watching = not self.watching

	def IsWatching(self):
		return self.watching
		
	def __StopRecording(self):
		self.md.StopRecording()

	def __SetState(self, state):
		if(self.__IsState(E_State.recording)):
			self.__StopRecording()
		self.state = state

	def __IsState(self, state):
		return self.state == state
	
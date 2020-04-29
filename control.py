from motionDetector import MotionDetector
from imutils.video import VideoStream
import time
import datetime
import os
import threading
from enum import Enum

class E_State(Enum):
	stopped = 0
	camera = 1
	recording = 2
	history = 3

class Control:
	def __init__(self, useFlaskReloader):
		self.md = MotionDetector(oneFrame=useFlaskReloader, motionDetectedCb=self.__motionDetected)
		self.title = ""
		self.videosDir = "./videos/"
		self.state = E_State.stopped
		self.playing = ""
		
		# Watcher
		self.maxWatcherRecordedDuration = 120
		self.minStopWatcherInactivity = 15
		self.watching = False
		self.motionEvent = threading.Event()
		self.lockControl = threading.RLock()
		self.watcherThread = threading.Thread(target=self.__updateWatching)
		self.watcherThread.daemon = True
		self.watcherThread.start()

		self.PlayNow()

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
		with self.lockControl:
			self.__SetState(E_State.history)
			self.title = "Playing: " + motion
			self.playing = motion
			if self.md.PlayFile(self.videosDir + motion):
				print ("Playing: " + motion)
			else:
				self.PlayNow()

	def PlayNow(self):
		with self.lockControl:
			if self.__IsState(E_State.camera):
				return
			self.__SetState(E_State.camera)
			self.title = "Camera"
			self.playing = "Camera"
			self.md.PlayCamera()
			print ("Starting camera")

	def Delete(self, motion):
		with self.lockControl:
			if self.playing == motion:
				self.Stop()
			os.remove(self.videosDir + motion)
			print ("Removing: " + motion)

	def __PruneVideos(self):
		print ("Removing old files:")
		# TODO

	def Stop(self):
		with self.lockControl:
			if self.__IsState(E_State.stopped):
				return
			self.__SetState(E_State.stopped)
			self.title = "Stopped"
			self.playing = ""
			self.md.Stop()
			print ("Stopped")

	def Record(self):
		with self.lockControl:
			wasRec = self.__IsState(E_State.recording)
			self.PlayNow()
			if not wasRec:
				self.__PruneVideos()
				timestamp = datetime.datetime.now()
				filename = timestamp.strftime("%d_%m_%y_%H_%M_%S.avi")
				if self.md.StartRecording(self.videosDir + filename):
					self.title = "Recording"
					self.__SetState(E_State.recording)

	def ToggleWatch(self):
		if not self.watching:
			self.PlayNow()
			self.watching = True
			print ("Watcher enabled")
		else:
			self.watching = False
			print ("Watcher disabled")
		
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

	def __motionDetected(self):
		if not self.motionEvent.isSet():
			print ("Motion detected")
			self.motionEvent.set()

	def __updateWatching(self):
		while True:
			if not self.__IsState(E_State.recording):
				if self.motionEvent.wait(30):
					if self.watching:
						self.Record()	# Start recording
				elif self.watching and not self.__IsState(E_State.camera) and not self.__IsState(E_State.recording):
					self.PlayNow() # Enable camera
					
			elif(self.GetLastMove() > self.minStopWatcherInactivity
			or self.GetLastDuration() > self.maxWatcherRecordedDuration
			or not self.watching):
				self.PlayNow()	# Stop recording
				if self.watching:
					time.sleep(10)
				self.motionEvent.clear()

			time.sleep(1)
	
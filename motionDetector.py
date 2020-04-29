import numpy as np
import imutils
import cv2
import threading
import time
import datetime

class MotionDetector:
	def __init__(self, oneFrame, motionDetectedCb, accumWeight=0.1):
		# Settings
		self.accumWeight = accumWeight
		self.weightedFramesMin = 32
		self.weghtedFramesProcessed = 0
		self.oneFrame = oneFrame
		self.videoWidth = 640
		self.videoHeight = 480
		self.videoFps = 30
		self.cameraInput = 0
		self.invalidInput = -1
		self.minInactivityduration = 15
		self.motionDetectedCb = motionDetectedCb

		# Streams
		self.outputFrame = None
		self.inputStream = None
		self.outputStream = None
		self.lockOutputFrame = threading.Lock()
		self.lockInputStream = threading.Lock()
		self.lockOutputStream = threading.Lock()

		# Stats
		self.motionDuration = 0
		self.lastMotion = datetime.datetime.now()

		self.bg = None
		self.playing = self.invalidInput
		self.PlayCamera()
		
		if(oneFrame): # Used for flask debug - threading block auto update
			self.CaptureFrames()
			self.inputStream.release()
		else:
			t = threading.Thread(target=self.CaptureFrames)
			t.daemon = True
			t.start()

	def __del__(self):
		if self.inputStream:
			self.inputStream.release()

	def PlayCamera(self):
		with self.lockInputStream:
			if self.playing == self.cameraInput:
				return
			return self.__PlayInput(self.cameraInput)

	def PlayFile(self, file):
		with self.lockInputStream:
			return self.__PlayInput(file)

	def Stop(self):
		with self.lockInputStream:
			self.__Stop()

	def __Stop(self):
		if self.inputStream:
			self.inputStream.release()
			self.inputStream = None
			self.playing = self.invalidInput
			#with self.lockOutputFrame:
			#	if self.outputFrame is not None:
			#		cv2.rectangle(self.outputFrame, (0, 0), (self.videoWidth, self.videoHeight), (220,220,220), thickness=cv2.FILLED)
		
	def __PlayInput(self, input):
		
		if self.inputStream:
			self.__Stop()

		if input == self.invalidInput:
			return

		time.sleep(0.2)
		self.inputStream = cv2.VideoCapture(input)
		self.inputStream.set(cv2.CAP_PROP_FRAME_WIDTH, self.videoWidth)
		self.inputStream.set(cv2.CAP_PROP_FRAME_HEIGHT, self.videoHeight)
		self.inputStream.set(cv2.CAP_PROP_FPS, self.videoFps)

		if not self.inputStream.isOpened():
				self.__Stop()
				return False
		self.playing = input
		return True

	def StartRecording(self, file):
		with self.lockOutputFrame:
			self.__StopRecording()
			fourcc = cv2.VideoWriter_fourcc(*'XVID')
			self.outputStream = cv2.VideoWriter(file, fourcc, self.videoFps, (self.videoWidth, self.videoHeight))
			if self.outputStream and self.outputStream.isOpened():
				print("Recording stared: " + file)
				return True
			else:
				print("Recording failed: " + file)
				return False

	def StopRecording(self):
		with self.lockOutputFrame:
			self.__StopRecording()

	def __StopRecording(self):
		if self.outputStream:
			print("Recording stopped")
			self.outputStream.release()
			self.outputStream = None

	def GenerateMultiJPEG(self):
		# loop over frames from the output stream
		while True:
			# wait until the lockOutputFrame is acquired
			with self.lockOutputFrame:
				# check if the output frame is available, otherwise skip
				# the iteration of the loop
				if self.outputFrame is None:
					continue
				# encode the frame in JPEG format
				(flag, encodedImage) = cv2.imencode(".jpg", self.outputFrame)
				# ensure the frame was successfully encoded
				if not flag:
					continue

			# yield the output frame in the byte format
			yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
				bytearray(encodedImage) + b'\r\n')
			
			if self.oneFrame:
				return

	def CaptureFrames(self):
		while True:
			ready = True
			with self.lockInputStream:
				if self.inputStream and self.inputStream.isOpened():
					ret, frame = self.inputStream.read()
				else:
					ready = False

				if not ready or not ret:
					self.__PlayInput(self.playing)
					continue	

			if self.playing == self.cameraInput:
				self.__ProcessMotion(frame)
				self.__DrawTimeStamp(frame)

			with self.lockOutputFrame:
				if self.outputStream:
					self.outputStream.write(frame)

			with self.lockOutputFrame:
				self.outputFrame = frame.copy()
			
			if(self.oneFrame):
				return

	def GetLastMove(self):
		return (datetime.datetime.now()-self.lastMotion).seconds

	def GetLastDuration(self):
		return self.motionDuration

	def __DrawTimeStamp(self, frame):
		timestamp = datetime.datetime.now()
		cv2.rectangle(frame, (0, 0), (220, 32), (255,255,255), thickness=cv2.FILLED)
		cv2.putText(frame, timestamp.strftime(
			"%d.%m.%y %H:%M:%S"), (5, 25),
			cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

	def __ProcessMotion(self, frame):
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		gray = cv2.GaussianBlur(gray, (7, 7), 0)
		
		if self.weghtedFramesProcessed > self.weightedFramesMin:
			motion = self.__DetectMotion(gray)
			if motion is not None:
				(thresh, (minX, minY, maxX, maxY)) = motion
				cv2.rectangle(frame, (minX, minY), (maxX, maxY),
					(0, 0, 255), 2)

				self.__RememberMotion(motion is not None)
				self.motionDetectedCb()
		
		self.__UpdateWeighted(gray)
		self.weghtedFramesProcessed += 1

	def __DetectMotion(self, image, tVal=25):
		# compute the absolute difference between the background model
		# and the image passed in, then threshold the delta image
		delta = cv2.absdiff(self.bg.astype("uint8"), image)
		thresh = cv2.threshold(delta, tVal, 255, cv2.THRESH_BINARY)[1]
		# perform a series of erosions and dilations to remove small
		# blobs
		thresh = cv2.erode(thresh, None, iterations=2)
		thresh = cv2.dilate(thresh, None, iterations=2)

		# find contours in the thresholded image and initialize the
		# minimum and maximum bounding box regions for motion
		cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
			cv2.CHAIN_APPROX_SIMPLE)
		cnts = imutils.grab_contours(cnts)
		(minX, minY) = (np.inf, np.inf)
		(maxX, maxY) = (-np.inf, -np.inf)

		# if no contours were found, return None
		if len(cnts) == 0:
			return None
		# otherwise, loop over the contours
		for c in cnts:
			# compute the bounding box of the contour and use it to
			# update the minimum and maximum bounding box regions
			(x, y, w, h) = cv2.boundingRect(c)
			(minX, minY) = (min(minX, x), min(minY, y))
			(maxX, maxY) = (max(maxX, x + w), max(maxY, y + h))
		# otherwise, return a tuple of the thresholded image along
		# with bounding box
		return (thresh, (minX, minY, maxX, maxY))

	def __UpdateWeighted(self, image):
		if self.bg is None:
			self.bg = image.copy().astype("float")
			return
		cv2.accumulateWeighted(image, self.bg, self.accumWeight)

	def __RememberMotion(self, movement):
		curTime = datetime.datetime.now()
		fromLast = curTime - self.lastMotion
		if movement:
			if fromLast.seconds < self.minInactivityduration:
				self.motionDuration += fromLast.seconds
			else:
				self.motionDuration = 0
			self.lastMotion = curTime
		else:
			self.motionDuration = 0
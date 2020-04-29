import pyaudio
import wave

# https://stackoverflow.com/questions/14140495/how-to-capture-a-video-and-audio-in-python-from-a-camera-or-webcam
# https://github.com/JRodrigoF/AVrecordeR
# https://raspberrypi.stackexchange.com/questions/89966/how-do-i-increase-the-input-volume-of-a-microphone-connected-to-pi-its-using-th
# arecord --device=hw:1,0 --format S16_LE --rate 44100 -V mono -c1 voice.wav

class AudioDetector():

	# Audio class based on pyAudio and Wave
	def __init__(self):
		self.open = True
		self.rate = 44100
		self.frames_per_buffer = 1024
		self.channels = 1
		self.format = pyaudio.paInt16
		self.audio_filename = "temp_audio.wav"
		self.audio = pyaudio.PyAudio()
		self.stream = self.audio.open(format=self.format,
																	channels=self.channels,
																	rate=self.rate,
																	input=True,
																	frames_per_buffer = self.frames_per_buffer)
		self.audio_frames = []

	# Audio starts being recorded
	def Record(self):
		self.stream.start_stream()
		while(self.open == True):
			data = self.stream.read(self.frames_per_buffer) 
			self.audio_frames.append(data)
			if self.open==False:
				break


	# Finishes the audio recording therefore the thread too    
	def Stop(self):
		if self.open==True:
			self.open = False
			self.stream.stop_stream()
			self.stream.close()
			self.audio.terminate()

			waveFile = wave.open(self.audio_filename, 'wb')
			waveFile.setnchannels(self.channels)
			waveFile.setsampwidth(self.audio.get_sample_size(self.format))
			waveFile.setframerate(self.rate)
			waveFile.writeframes(b''.join(self.audio_frames))
			waveFile.close()

		pass

    # Launches the audio recording function using a thread
	def Start(self):
		audio_thread = threading.Thread(target=self.Record)
		audio_thread.start()
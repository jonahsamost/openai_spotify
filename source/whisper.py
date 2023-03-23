import openai

import io
import os
import speech_recognition as sr

from datetime import datetime, timedelta
from queue import Queue
from tempfile import NamedTemporaryFile
from time import sleep
from sys import platform

openai.api_key = os.getenv("OPENAI_API_KEY")
END_SEQUENCE = 'done talking'

def sendWhisperRequestWithFile(filename):
  audio_file = open(filename, "rb")
  transcript = openai.Audio.transcribe("whisper-1", audio_file)
  return transcript['text'] if 'text' in transcript else ''

def isDoneSpeaking(text):
  return text.lower().find(END_SEQUENCE) != -1

def captureAudioReturnResult():
    # energy level for mic to detect
    energy_threshold = 1000
    # How real time the recording is in seconds."
    record_timeout = 2
    # How much empty space between recordings before 
    # we consider it a new line in the transcription
    phrase_timeout = 1
    default_microphone = 'pulse'
      
    
    # The last time a recording was retreived from the queue.
    phrase_time = None
    # Current raw audio bytes.
    last_sample = bytes()
    # Thread safe Queue for passing data from the threaded recording callback.
    data_queue = Queue()
    # We use SpeechRecognizer to record our audio because it has a nice feauture where it can detect when speech ends.
    recorder = sr.Recognizer()
    recorder.energy_threshold = energy_threshold
    # Definitely do this, dynamic energy compensation lowers the energy threshold dramtically to a point where the SpeechRecognizer never stops recording.
    recorder.dynamic_energy_threshold = False
    
    # Important for linux users. 
    # Prevents permanent application hang and crash by using the wrong Microphone
    if 'linux' in platform:
      for index, name in enumerate(sr.Microphone.list_microphone_names()):
        if name == default_microphone:
          source = sr.Microphone(sample_rate=16000, device_index=index)
          print('Found correct microphone!')
          break
    else:
      source = sr.Microphone(sample_rate=16000)
        
    # Load / Download model
    # model = args.model
    # if args.model != "large" and not args.non_english:
    #     model = model + ".en"
    # audio_model = whisper.load_model(model)

    transcription = ['']
    
    with source:
      recorder.adjust_for_ambient_noise(source)

    def record_callback(_, audio:sr.AudioData) -> None:
      """
      Threaded callback function to recieve audio data when recordings finish.
      audio: An AudioData containing the recorded bytes.
      """
      # Grab the raw bytes and push it into the thread safe queue.
      data = audio.get_raw_data()
      data_queue.put(data)

    # Create a background thread that will pass us raw audio bytes.
    # We could do this manually but SpeechRecognizer provides a nice helper.
    recorder.listen_in_background(source, record_callback, phrase_time_limit=record_timeout)

    # Cue the user that we're ready to go.
    print("Listening...")

    bytes_written = False
    all_text = ''

    temp_file = '/tmp/listen.wav'
    while True:
      try:
        now = datetime.utcnow()
        # Pull raw recorded audio from the queue.
        if not data_queue.empty():
          phrase_complete = False
          # If enough time has passed between recordings, consider the phrase complete.
          # Clear the current working audio buffer to start over with the new data.
          if bytes_written and phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
            print('phrase complete!')
            last_sample = bytes()
            phrase_complete = True
          # This is the last time we received new audio data from the queue.
          phrase_time = now

          # Concatenate our current audio data with the latest audio data.
          while not data_queue.empty():
            data = data_queue.get()
            last_sample += data

          # Use AudioData to convert the raw data to wav data.
          audio_data = sr.AudioData(last_sample, source.SAMPLE_RATE, source.SAMPLE_WIDTH)
          wav_data = io.BytesIO(audio_data.get_wav_data())

          # Write wav data to the temporary file as bytes.
          with open(temp_file, 'w+b') as f:
            print('writing bytes')
            bytes_written = True
            f.write(wav_data.read())

          whisper_txt = sendWhisperRequestWithFile(temp_file)
          print(whisper_txt)
          all_text += ' ' + whisper_txt
          if isDoneSpeaking(whisper_txt):
            all_text = all_text.lower().replace(END_SEQUENCE, '')
            all_text = all_text.replace('...', ' ')
            print('Complete message: ', all_text)
            # os.remove(temp_file)
            return all_text
            break

          sleep(0.1)
      except KeyboardInterrupt:
          break


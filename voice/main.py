import speech_recognition as sr
import pyttsx3

recognizer = sr.Recognizer()
speaker = pyttsx3.init()


def speak(text):
    print("AI:", text)
    speaker.say(text)
    speaker.runAndWait()


def listen():
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source)

    try:
        return recognizer.recognize_google(audio, language="en-IN")
    except sr.UnknownValueError:
        return "Sorry, I could not understand."
    except sr.RequestError:
        return "Speech recognition service is unavailable."


speak("Welcome to Student AI Assistant")
question = listen()
print("You:", question)
speak("You said: " + question)
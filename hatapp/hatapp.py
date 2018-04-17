#!/usr/bin/env python3

from kivy.config import Config
Config.set('graphics', 'fullscreen', 'auto')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.uix.gridlayout import GridLayout
from kivy.uix.layout import Layout
from kivy.uix.image import Image
from kivy.uix.carousel import Carousel
from kivy.graphics.texture import Texture
from kivy.graphics import *
from kivy.clock import Clock

import glob

from kivy.uix.screenmanager import ScreenManager, Screen


import subprocess

class HatApp(App):
    def build(self):
        self.screens = {}
        self.available_screens = ['Slideshow', 'SeeSay']
        self.sp = None
        self.oldies_but_happies = "mpg123 /home/pi/oldies_but_happies.mp3"
        self.wintergartan = "mpg123 /home/pi/wintergartan.mpeg"
        self.candyman = "mpg123 /home/pi/candy_man.mp3"
        # self.image_slideshow = "DISPLAY=:0 feh -FZz -D1 --auto-rotate /home/pi/Pictures/*"
        self.image_slideshow = """DISPLAY=:0 feh -FZz -D1 --auto-rotate /home/pi/Pictures/* &
        echo '"pkill -n feh; pkill -n xbindkeys"'>xbindkeys.temp
        echo "b:1">>xbindkeys.temp
        xbindkeys -n -f xbindkeys.temp
        rm xbindkeys.temp
        """

        # return MainScreen()

    def open_screen(self, screen):
        self.root.ids.im.switch_to(self.load_screen(screen), direction='left')

    def load_screen(self, screen):
        if screen in self.screens:
            return self.screens[screen]
        screen_obj = Builder.load_file(screen)
        self.screens[screen] = screen_obj
        return screen_obj

    def run_subprocess(self, command: str) -> subprocess.Popen:
        if self.sp is not None:
            try:
                self.sp.kill()
            except:
                pass
        self.sp = subprocess.Popen(["bash", "-c", command])

import cv2
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera
from tensorflow import keras
import os
import json
import tempfile
from functools import partial
from kivy.core.text import Label as CoreLabel

def main_menu():
    App.get_running_app().root.current = 'menu'

class ShowcaseScreen(Screen):
    img_paths = glob.glob('/home/pi/Pictures/*.jpg') + glob.glob('/home/pi/Pictures/*.jpg')
    camera = None
    iv3 = None
    api_data = None
    image_widget = None

    def on_pre_enter(self):
        self.canvas.clear()
        Clock.schedule_once(lambda x: self.cap_and_display(), 1)

    def cap_and_display(self):
        print('capturing image')
        self.image_widget = Image()
        texture = Texture.create(size=(800,480))
        self.im = self.get_image()
        texture.blit_buffer(self.im.tostring(), bufferfmt='ubyte', colorfmt='rgb')
        with self.canvas:
            Rectangle(texture=texture, pos=self.pos, size=(800,480))
        self.canvas.ask_update()
        Clock.schedule_once(lambda x: self.infer_and_speak(), 0.1)

    def infer_and_speak(self):
        scaled_im = self.scale_image(self.im)
        name = self.predict(scaled_im)
        stimulus, response = self.category_to_thought(name)
        string_to_speak = ". When I see {}, I think of {}.".format(stimulus, response)
        string_to_speak = string_to_speak.replace('_', ' ')
        self.say_something(string_to_speak)
        self.annotate_image(string_to_speak)
 
        Clock.schedule_once(lambda x: main_menu(), 7)

    def annotate_image(self, string):
        top_text, bot_text = string.split(',')
        top_label = CoreLabel(text=top_text, font_size=50, text_size=(800, 80), halign='center', valign='top', outline_width=10, outline_color=(50,50,50))
        bot_label = CoreLabel(text=bot_text, font_size=50, text_size=(800, 80), halign='center', valign='bottom', outline_width=10)
        top_label.refresh()
        bot_label.refresh()
        top_tex = top_label.texture
        bot_tex = bot_label.texture
        with self.canvas:
            Color(0,0,0)
            Rectangle(size=top_tex.size, pos=(0,400))
            Rectangle(size=bot_tex.size, pos=(0,0))
            Color(255,255,255)
            Rectangle(size=top_tex.size, pos=(0,400), texture=top_tex)
            Rectangle(size=bot_tex.size, pos=(0,0), texture=bot_tex)
        pass

    def see_say(self):
        self.image_widget = Image()
        texture = Texture.create(size=(800,480))
        self.im = self.get_image()
        texture.blit_buffer(self.im.tostring(), bufferfmt='ubyte', colorfmt='rgb')
        with self.canvas:
            Rectangle(texture=texture, pos=self.pos, size=(800,480))
        scaled_im = self.scale_image(self.im)
        name = self.predict(scaled_im)
        stimulus, response = self.category_to_thought(name)
        string_to_speak = ". When I see {}, I think of {}.".format(stimulus, response)
        string_to_speak = string_to_speak.replace('_', ' ')
        self.say_something(string_to_speak)

        Clock.schedule_once(lambda x: main_menu(), 5)

    def get_image(self):
        if self.camera is None:
            self.camera = PiCamera()
        rawCapture = PiRGBArray(self.camera)
        self.camera.capture(rawCapture, format="rgb")
        image = rawCapture.array
        return image

    def scale_image(self, image):
        small_image = cv2.resize(image[0:480, 160:640], dsize=(299,299))
        small_image_f32 = np.float32(small_image)
        small_image_f32_r3 = np.expand_dims(small_image_f32, 0)
        scaled_image = small_image_f32_r3/255
        return scaled_image

    def predict_image(self, im):
        if self.iv3 is None:
            self.iv3 = keras.applications.InceptionV3(
                    include_top=True,
                    weights='imagenet',
                    input_tensor=None,
                    input_shape=None,
                    pooling=None,
                    classes=1000
                    )
        prediction = self.iv3.predict(im)
        return keras.applications.inception_v3.decode_predictions(prediction)

    def predict(self, im):
        prediction = self.predict_image(im)
        name = prediction[0][1][1]
        return name

    def say_something(self, text):
        number, fname = tempfile.mkstemp(suffix='.wav')
        command = 'pico2wave --wave={} -len-GB "{}" && aplay {} && rm {}'.format(
                fname,
                text,
                fname,
                fname
                )
        subprocess.Popen(['bash', '-c', command])

    def category_to_thought(self, category):
        if self.api_data is None:
            with open('./joern_api_responses.json', 'r') as f:
                self.thought_responses  = json.load(f)
        retval = None
        try:
            retval = self.thought_responses[category]
        except:
            retval = [category, "Beer"]
        return retval

class MyScreenManager(ScreenManager):
    def new_color_screen(self):
        s = Screen(name=name)
        self.add_widget(s)
        self.current = name

class MenuScreen(Screen):
    pass



if __name__ == '__main__':
    HatApp().run()

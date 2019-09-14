from tkinter import *
from PIL import Image,ImageTk
import random
import numpy as np
import cv2
import sys
import time
import math
import collections
import coloredlogs, logging
import pygetwindow as pgw
from screen_move import execute_action
from screen_move import get_action_num

sys.setrecursionlimit(10000)
####################################
# customize these functions
####################################


def init(data):
    
    data.binary = None
    data.box = None
    data.object_color = data.frame[105:175, 505:575]
    data.cnt = None
    data.com = (0,0)
    data.prev_window = pgw.getActiveWindow()
    data.count = 0
    data.old_com = (0,0)
    
def mouseMotion(event, data):
    data.cursorX, data.cursorY = event.x, event.y

        
def keyPressed(event, data):
    if event.keysym == "a":
       data.object_color = data.box
    elif event.keysym == "s":
       print(data.com)
        
def timerFired(data):
    return None


def cursorPositionStart(canvas, data):
    return None


def opencvToTk(frame):
    """Convert an opencv image to a tkinter image, to display in canvas."""
    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_image)
    tk_image = ImageTk.PhotoImage(image=pil_img)
    return tk_image

    
def get_center_of_mass(data):
        if len(data.cnt) == 0:
            return None
        M = cv2.moments(data.cnt)
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        return (cX, cY)
        
def detectHand(data):
    palm_area = 0;
    min_area = 10000;
    color=(0, 255, 0);
    thickness = 2;
    
    cv2.rectangle(data.frame, (500, 100), (580, 180), (105, 105, 105), 2)
    data.box = data.frame[105:175, 505:575]
        
    object_color_hsv = cv2.cvtColor(data.object_color, cv2.COLOR_BGR2HSV)
    object_hist = cv2.calcHist([object_color_hsv], [0, 1], None,
                               [12, 15], [0, 180, 0, 256])
    cv2.normalize(object_hist, object_hist, 0, 255, cv2.NORM_MINMAX)
    hsv_frame = cv2.cvtColor(data.frame, cv2.COLOR_BGR2HSV)
    object_segment = cv2.calcBackProject(
        [hsv_frame], [0, 1], object_hist, [0, 180, 0, 256], 1)

    disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    cv2.filter2D(object_segment, -1, disc, object_segment)
    _, segment_thresh = cv2.threshold(
        object_segment, 70, 255, cv2.THRESH_BINARY)
        
        
    kernel = None
    eroded = cv2.erode(segment_thresh, kernel, iterations=2)
    dilated = cv2.dilate(eroded, kernel, iterations=2)
    binary = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel)
    data.cnt,_ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    for (i, c) in enumerate(data.cnt):
            area = cv2.contourArea(c)
            if area > palm_area:
                palm_area = area
                flag = i
                
    if flag is not None and palm_area > min_area:
        data.cnt = data.cnt[flag]
        # cpy = data.frame.copy()
        cv2.drawContours(data.frame, [data.cnt], 0, color, thickness)
        data.com = get_center_of_mass(data)
        cv2.circle(data.frame, data.com, 10, (255, 0, 0), -1)
        return data.frame
    else:
        return data.frame
                

def detectFace(data, block=False, colour=(0, 0, 0)):
    fill = [1, -1][block]
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(data.frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5)
    area = 0
    X = Y = W = H = 0
    for (x, y, w, h) in faces:
        if w * h > area:
            area = w * h
            X, Y, W, H = x, y, w, h
    cv2.rectangle(data.frame, (X, Y), (X + W, Y + H), colour, fill)

def drawCamera(canvas, data):
    _, data.frame = data.camera.read()
    data.frame = cv2.flip(data.frame,1)
    detectHand(data)
    #detectFace(data, block=True)
    data.tk_image = opencvToTk(data.frame)
    canvas.create_image(data.width/2, data.height/2, image=data.tk_image)

def redrawAll(canvas, data):
    drawCamera(canvas, data)

####################################
# use the run function as-is
####################################

def run(width=500, height=500):
    def redrawAllWrapper(canvas, data):
        canvas.delete(ALL)
        canvas.create_rectangle(0, 0, data.width, data.height,
                                 fill='white', width=0)
        redrawAll(canvas, data)
        canvas.update()   

    def mousePressedWrapper(event, canvas, data):
        mousePressed(event, data)
        redrawAllWrapper(canvas, data)

    def keyPressedWrapper(event, canvas, data):
        keyPressed(event, data)
        redrawAllWrapper(canvas, data)

    def timerFiredWrapper(canvas, data):
        timerFired(data)
        redrawAllWrapper(canvas, data)
        data.count += 1
        if(data.count % 20 == 0):
            (new_cx, new_cy) = data.com
            (old_cx, old_cy) = data.old_com
            num_fingers = 2
            action = get_action_num(old_cx, old_cy, new_cx, new_cy, data.width,data.height, num_fingers)
            print(action)
            # data.prev_window = execute_action(action, cx, cy, data.prev_window)
            data.old_com = (new_cx, new_cy)
        # pause, then call timerFired again
        canvas.after(data.timerDelay, timerFiredWrapper, canvas, data)
        
    def mouseMotionWrapper(event, canvas, data):
        #if data.useMotion == True:
        mouseMotion(event, data)
        #redrawAllWrapper(canvas, data)

    # Set up data and call init
    class Struct(object): pass
    data = Struct()
    data.width = width
    data.height = height
    data.cameraIndex = 0
    camera = cv2.VideoCapture(data.cameraIndex)
    data.camera = camera

    data.timerDelay = 10 # milliseconds
    _, data.frame = data.camera.read()
    data.frame = cv2.flip(data.frame,1)
    init(data)
    # create the root and the canvas
    root = Tk()
    canvas = Canvas(root, width=data.width, height=data.height)
    canvas.pack()
    # set up events
    root.bind("<Button-1>", lambda event:
                            mousePressedWrapper(event, canvas, data))
    root.bind("<Key>", lambda event:
                            keyPressedWrapper(event, canvas, data))
    root.bind('<Motion>', lambda event:
                            mouseMotionWrapper(event, canvas, data))
    timerFiredWrapper(canvas, data)
    
    # and launch the app
    root.mainloop()  # blocks until window is closed
    data.camera.release()
    print("bye!")



if __name__ == "__main__":
    run(1000, 600)
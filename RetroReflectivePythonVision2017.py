import cv2
import numpy as np
import math

from collections import namedtuple

# tuning purposes
DEBUG_ALL = False
DEBUG_SHOW_RAW_CAMERA = False
DEBUG_RETRO_READING = False
DEBUG_TUNE_RETRO_READING = False
DEBUG_SHAPE_FINDING = True

# how many times should a "a vote" to go either left or right should win before it's outputted to the robot
VOTE_COUNT = 100

Direction = namedtuple("Direction", "left, straight, right")
Point = namedtuple("Point", "x, y")
Rectangle = namedtuple("Rectangle", "top_left, top_right, bottom_left, bottom_right")

vid = cv2.VideoCapture(0)

lower_green = np.array([85,140,250])
upper_green = np.array([95,255,255])

def about_the_same(num_1, num_2, diff = 3):
    return abs(num_1 - num_2) <= diff

def rectangle_not_too_small(rect): #[which corner][0][x or y component]
    too_small = False
    for i in range(0, len(rect)):
        for j in range(0, len(rect)):
            too_small = about_the_same(rect[i][0][0], rect[j][0][0], diff = 10) and about_the_same(rect[i][0][1], rect[j][0][1], diff = 10)
    return not too_small

def rectangles_are_similar(rect_1, rect_2):
    for i in range(0, len(rect_1)):
        for j in range(0, len(rect_2)):
            if i == j:
                continue
            if about_the_same(rect_1[i][0][0], rect_2[j][0][0]) and about_the_same(rect_1[i][0][1], rect_2[j][0][1]):
                return True
    return False

# BUG?
def boxes_to_rect(box): #[which corner][0][x or y component]
    lower_x = box[0][0][0]
    upper_x = box[0][0][0]
    lower_y = box[0][0][1]
    upper_y = box[0][0][1]

    # loops through corners in box and finds lowest and highest x's and y's
    for i in range(1, len(box)):
        if box[i][0][0] <= lower_x:
            lower_x = box[i][0][0]
        elif box[i][0][0] > upper_x:
            upper_x = box[i][0][0]

        if box[i][0][1] <= lower_y:
            lower_y = box[i][0][1]
        elif box[i][0][1] > upper_y:
            upper_y = box[i][0][1]

    return Rectangle(Point(lower_x, lower_y), Point(upper_x, lower_y), Point(lower_x, upper_y), Point(upper_x, upper_y))


# returns a Direction
def where_should_i_go(result):
    #out_file = open('output.txt', 'w+')
    gray = cv2.cvtColor(result,cv2.COLOR_BGR2GRAY)
    canny = cv2.Canny(gray, 50, 150, apertureSize = 3)
    #height, width = canny.shape

    im2, contours, h = cv2.findContours(canny, 1, cv2.CHAIN_APPROX_SIMPLE)
    #print("contours", len(contours))
    guidingBoxes = []
    if len(contours) > 0:
        for contour in contours:
            approx = cv2.approxPolyDP(contour, 0.10 * cv2.arcLength(contour, True), True)
            if len(approx) == 4:
                if DEBUG_ALL or DEBUG_SHAPE_FINDING:
                    # print("next: \n")
                    # [which corner][0][x or y component]
                    # print(approx[0][0][0])
                    cv2.drawContours(result, [contour], 0, (0, 0, 255), -1)
                    cv2.imshow("DEBUG_SHAPE_FINDING", result)
                if len(guidingBoxes) == 0:
                    guidingBoxes.append(approx)
                elif len(guidingBoxes) == 1:
                    #for box in guidingBoxes:
                    if(not rectangles_are_similar(guidingBoxes[0], approx)) and rectangle_not_too_small(approx):
                        guidingBoxes.append(approx)
    elif DEBUG_ALL or DEBUG_SHAPE_FINDING:
        print("NO SHAPES FOUND")
        return "0"
    else:
        print(0)
        return "0"

    # which box is left (other is right)
    if len(guidingBoxes) > 2:
        print("TOO MUCH INTERFERENCE!!!")
        return "nowhere"
    elif len(guidingBoxes) < 2:
        print("OBSTRUCTION BOTH BOXES NOT FOUND")
        return "nowhere"
    '''''
    print(guidingBoxes[0])
    print(guidingBoxes[1])
    cv2.waitKey(1000)
    exit()'''''

    # the entirety of the left box should be to the left of the right box as they neither overlap nor touch
    left_box_index = (0 if guidingBoxes[0][0][0][0] < guidingBoxes[1][0][0][0] else 1)
    if left_box_index == 0:
        right_box_index = 1
    else:
        right_box_index = 0

    try:
        # @bug before here
        rect_left = boxes_to_rect(guidingBoxes[left_box_index]) #[which corner][0][x or y component]
        rect_right = boxes_to_rect(guidingBoxes[right_box_index])
        # little is lesser than big
        if((abs(rect_right.top_left.x - rect_left.top_right.x) * 2) < (abs(rect_right.top_left.x - rect_left.top_left.x))):
            print("BOXES ARE TOO CLOSE")
            return 0

        '''
        print("rect_right.top_left.y", rect_right.top_left.y)
        print("rect_right.bottom_left.y", rect_right.bottom_left.y)
        print("rect_right.top_right.y", rect_right.top_right.y)
        print("rect_right.bottom_right.y", rect_right.bottom_right.y)

        print("rect_left.top_left.y", rect_left.top_left.y)
        print("rect_left.bottom_left.y", rect_left.bottom_left.y)
        print("rect_left.top_right.y", rect_left.top_right.y)
        print("rect_left.bottom_right.y", rect_left.bottom_right.y)
        '''

        # should all be ys
        right_side_avg = ((rect_right.bottom_right.y - rect_right.top_right.y) + (rect_left.bottom_right.y - rect_left.top_right.y)) / 2
        left_side_avg = ((rect_right.bottom_left.y - rect_right.top_left.y) + (rect_left.bottom_left.y - rect_left.top_left.y)) / 2

        #out_file.write("left_side_avg", left_side_avg)
        #out_file.write("right_side_avg", right_side_avg)

        # 10% the same is good enough
        if about_the_same(right_side_avg, left_side_avg, diff = (((right_box_index + left_side_avg) / 2) * .10)):
            print("S")
            return "S"
        elif right_side_avg > left_side_avg:
            print("R")
            return "R"
        elif left_side_avg > right_side_avg:
            print("L")
            return "L"

    except UnboundLocalError:
        print("Boxes to rectangle FAILED")
        return 0

    return 0


# Testing purposes!!
def on_mouse(k, x, y, s, p):
    global hsv

    if k == 1:   # left mouse, print pixel at x,y
        print(hsv[y, x])


# this sends the results of whether the robot should rotate left or right or go straight to the robot
def OUTPUT(where_i_should_go):
    #note to robot: if this code says go right followed by go left, or vice versa => go straight
    #setup to return 3 directions, capable of more (5 easily) aka (big vs little)left vs straight vs (big vs little)right
    #    could theorectically take exact ratios for approximate "exact" movement to go
    print("exiting python")
    print("The Robot should go ", where_i_should_go)
    exit()

# votes to go left are negative, to the right are positive
votes = Direction(0, 0, 0)
while True and (votes.left < 100) and (votes.straight < 100) and (votes.right < 100):
    ret, frame = vid.read()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_green, upper_green)
    result = cv2.bitwise_and(frame, frame, mask=mask)

    if DEBUG_ALL or DEBUG_SHOW_RAW_CAMERA:
        cv2.imshow('original',frame)

    if DEBUG_ALL or DEBUG_RETRO_READING:
        cv2.namedWindow("DEBUG_RETRO_READING")
        cv2.setMouseCallback("DEBUG_RETRO_READING", on_mouse)
        cv2.imshow('DEBUG_RETRO_READING',result)

    if DEBUG_ALL or DEBUG_TUNE_RETRO_READING:
        cv2.namedWindow("DEBUG_RETRO_TUNING")
        cv2.setMouseCallback("DEBUG_RETRO_TUNING", on_mouse)
        cv2.imshow('DEBUG_RETRO_TUNING', frame)



    to_where_should_i_go = where_should_i_go(result)

    if to_where_should_i_go == "L":
        votes = Direction(1 + votes.left, votes.straight, votes.right)
    elif to_where_should_i_go == "R":
        votes = Direction(votes.left, votes.straight, 1 + votes.right)
    elif to_where_should_i_go == "S":
        votes = Direction(votes.left, 1 + votes.straight, votes.right)

    if(votes.left >= VOTE_COUNT):
        if(votes.right >= VOTE_COUNT * .5 or votes.straight >= VOTE_COUNT * .3):
            OUTPUT("S")
        else:
            OUTPUT("L")
    elif(votes.right >= VOTE_COUNT):
        if(votes.left >= VOTE_COUNT * .5 or votes.straight >= VOTE_COUNT * .3):
            OUTPUT("S")
        else:
            OUTPUT("R")
    elif(votes.straight >= VOTE_COUNT):
        OUTPUT("S")


    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
vid.release()
cv2.destroyAllWindows()
#out_file.close()

##### RANGE VALUE TUNING (50-95, 0-90, 250-255)

'''
video_cap = cv2.VideoCapture(0)

def onmouse(k, x, y, s, p):
    global hsv

    if k == 1:   # left mouse, print pixel at x,y
        print(hsv[y, x])

while True:
    ret, frame = video_cap.read()

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    cv2.namedWindow("hsv")
    cv2.setMouseCallback("hsv", onmouse)
    cv2.imshow('hsv', hsv)



    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.namedWindow("hsv")
cv2.setMouseCallback("hsv", onmouse)
cv2.imshow('hsv', hsv)

cv2.waitKey(10000)

cv2.destroyAllWindows()
video_cap.release()
'''
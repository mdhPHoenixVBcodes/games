import turtle
import math
import os
import time
import random

t = turtle.Turtle()
time.sleep(3)
print ("Welcome to the Turtle Game!")
print ("To exit the game, type 'exit' in the movement prompt.")
print ("Loading map...")
time.sleep(2)
os.system('cls')
t.left(90)
while True:
    os.system('cls')
    movement_input = input("How much do you want to move? ")

    if not movement_input.strip():
        os.system('cls')
        print("Try again")
        time.sleep(1)
        continue

    if movement_input == 'exit':
        break
        os.system('cls')
    elif movement_input == 'restart':
        t.reset()
        t.left(90)
        os.system('cls')
        continue

    try:
        movement = int(movement_input)
    except ValueError:
        os.system('cls')
        print("Please enter a number or a command (exit/restart)")
        time.sleep(1)
        continue

    t.forward(movement)
    os.system('cls')
    
    yorn = input("Do you want to turn [y or n]? ")
    if yorn.lower() == 'y':
        turner = input("Where do you want to turn? [r or l] - ")
        if turner.lower() in ['r', 'right']:
            os.system('cls')
            try:
                vement = int(input("How much do you want to turn right? "))
                t.right(vement)
            except ValueError:
                print("Invalid number")
                time.sleep(1)
        elif turner.lower() in ['l', 'left']:
            os.system('cls')
            try:
                vement = int(input("How much do you want to turn left? "))
                t.left(vement)
            except ValueError:
                print("Invalid number")
                time.sleep(1)

    
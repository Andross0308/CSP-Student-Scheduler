
# What the program does 

This project uses a CSP model to create a schedule for a week, given a certain number of tasks, that could be fixed and 
obligatory or flexible and optional. The model determines the best solution of the one that has the biggest weight overall

# How to run:
 - Python version 3.14.0
 - File named "Library.json"
 - install ortools
 - run using "python main.py"

# Input Format 

The file receives input from 2 places, the first is using an API to the Goggle Calendar that receives the schedule as it is
The second is the new task, an input of the user, that is converted into JSON using an API of the OpenAI bot

The tasks are created in the following formats:
 - A fixed Task uses the name as key, kind is "fixed_task", day is the day it occurs and start/end indicate the window of that task:
          "Aula BD Pratica": {
              "kind": "fixed_task", 
              "day": "Terça", 
              "start": "16:00", 
              "end": "18:00"
          }

   - An optional task as mostly the same format, but uses a domain dict to store all possible windows the task can occur with a durationMin and durationMax to happen and weight:
   Gym": {
      "kind": "optional_task",
      "domains": [
        {
          "day": "Segunda",
          "start": "8:00",
          "end": "21:00"
        },
        {
          "day": "Terça",
          "start": "8:00",
          "end": "21:00"
        }
      ],
      "durationMin": 60,
      "durationMax": 60,
      "weight": 3
}

# Output Format
The output is the new task, asked by the user, is added into Google calendar using the API after confirmation of the user

# Design Choices:
 - Counting minutes since the beginning of the week to calculate the schedule
 - Objects Oriented Program using different classes and objects to give extra security to the projects

# Limitations:
 - The objective doesn't look for the "best time to put a new task", only puts in the first new available window
 - The solver not accepting a new task if the window for it is filled, instead of trying to find a solution that makes the both accepted
 - The model doesn't use dynamic weighting, so it gives the same importances to all the task, no matter the rest in the schedule(For example, doesn't increase the importance of studying in test periods)

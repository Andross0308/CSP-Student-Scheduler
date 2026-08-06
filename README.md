# What the program does 

This project uses a CSP model to create a schedule for a week, given a certain number of tasks, that could be fixed and 
obligatory or flexible and optional. The model determines the best solution of the one that has the biggest weight overall

# How to run:
 - Python version 3.14.0
 - File named "Tasks.json"
 - install ortools
 - run using "python main.py"

# Input Format (Tasks.json)
    
Two elements, named "fixedTasks" and "optionalTasks", both have a list of elements
    
The elements on the "fixedTasks" list have name, day, HoraInicio and HoraFim
    
    { "name": "Aula BD Pratica", "day": "Terça", "HoraInicio": "16:00", "HoraFim": "18:00"}
    
The elements on the "optionalTasks" list have name, domains, durationMin, durationMax and peso. domains also has a list of elements of all the possible intervals the task could happen, with a day, HoraInicio, HoraFim

    {"name": "Gym", "domains": [ {"day": "Segunda", "HoraInicio": "8:00", "HoraFim": "21:00"}, {"day": "Terça", "HoraInicio": "8:00", "HoraFim": "21:00"}], "durationMin": 60, "durationMax": 60, "peso": 3}

# Output Format (output.json)

The file contains a list of elements that posses a name, start and end, both start and end have their elements, being day, hour and minute

    {"name": "Aula BD Pratica", "start": {"day": "Terça", "hour": 16, "minute": 0}, "end": {"day": "Terça", "hour": 18, "minute": 0}}

# Design Choices:
 - Counting minutes since the beginning of the week to calculate the schedule
 - Fixed and optional tasks in different lists because of the different elements on both, easier to loop over them 

# Limitations:
 - Only works in a week, doesn't work on a schedule of different weeks
 - The objective only values weight of task, doesn't consider balance between days, breaks or other factors to choosing the schedule

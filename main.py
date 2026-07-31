from ortools.sat.python import cp_model

def minutesOfTheWeek(day, hour, minutes):
    """
    Calculates the minutes since the start of the week to the given time
    :param day: Day of the week
    :param hour: Hour of the given time
    :param minutes: Minutes of the given time
    :return: the time in minutes since the start of the week
    """
    return day * 1440 + hour * 60 + minutes

model = cp_model.CpModel()

#All time intervals that the model receives
tasks = {}
intervals = []
boolean_variables = []
pesos = []

def fixedTasks():
    tasks = [("Aula BD Pratica", ("Terça", "16:00"), ("Terça", "18:00"), minutesOfTheWeek(1, 16, 0),
              minutesOfTheWeek(1, 18, 0)),
             ("Aula LAP Pratica", ("Terça", "14:00"), ("Terça", "16:00"), minutesOfTheWeek(1, 14, 0),
              minutesOfTheWeek(1, 16, 0)),
             ("Aula PED Pratica", ("Segunda", "10:00"), ("Segunda", "12:00"), minutesOfTheWeek(0, 10, 0),
              minutesOfTheWeek(0, 12, 0)),
             ("Aula TC Pratica", ("Segunda", "8:00"), ("Segunda", "10:00"), minutesOfTheWeek(0, 8, 0),
              minutesOfTheWeek(0, 10, 0)),
             ("Aula BD Teorica", ("Quarta", "10:00"), ("Quarta", "11:30"), minutesOfTheWeek(2, 10, 0),
              minutesOfTheWeek(2, 11, 30)),
             ("Aula LAP Teorica", ("Quinta", "11:30"), ("Quinta", "13:00"), minutesOfTheWeek(3, 11, 30),
              minutesOfTheWeek(3, 13, 0)),
             ]
    for nome,_,_, begin, end in tasks:
        duration = end - begin
        interval = model.new_interval_var(begin, duration,end, nome)
        intervals.append(interval)


def createNewOptionalTask(name, domainStart, domainEnd, durationMin, durationMax, peso):
    bool_var = model.new_bool_var(f"{name}_Present")
    boolean_variables.append(bool_var)
    startDomain = cp_model.Domain.FromIntervals([[domainStart, domainEnd]])
    start = model.new_int_var_from_domain(startDomain, f"{name}_Start")
    duration = model.new_int_var(durationMin, durationMax, f"{name}_Duration")
    endDomain =  cp_model.Domain.FromIntervals([[domainStart + durationMin, domainEnd + durationMax]])
    end = model.new_int_var_from_domain(endDomain, f"{name}_End")
    model.add(start + duration == end)
    var = model.new_optional_interval_var(start, duration, end, bool_var, f"{name}_Interval")
    intervals.append(var)
    pesos.append(peso)
    tasks[name] = {"bool": bool_var, "start": start, "duration": duration, "end": end}

fixedTasks()
createNewOptionalTask("Gym", minutesOfTheWeek(0, 8, 0), minutesOfTheWeek(0, 21, 0)
                      , 60, 60, 3)
createNewOptionalTask("Chess", minutesOfTheWeek(0, 8, 0), minutesOfTheWeek(0, 21, 0)
                      , 30, 30, 2)
createNewOptionalTask("Study", minutesOfTheWeek(0, 10, 00), minutesOfTheWeek(0, 16, 00),
                      30, 120, 5)
createNewOptionalTask("Library", minutesOfTheWeek(0, 10, 00), minutesOfTheWeek(0, 16, 00),
                      60, 180, 5)

"Gym Optional Task"
"""
bool_var = model.new_bool_var("Ginasio_Presente")
boolean_variables.append(bool_var)
dominio = cp_model.Domain.FromIntervals([[minutesOfTheWeek(0, 8, 0), minutesOfTheWeek(0, 21, 0)]])
Gym = model.new_int_var_from_domain(dominio, "Ginasio")
gym_var = model.new_optional_interval_var(Gym, 60, Gym + 60, bool_var, "Ginasio_Interval")
intervals.append(gym_var)

"Chess Optional Task"
chess_var = model.new_bool_var("Xadrez_Presente")
boolean_variables.append(chess_var)
Chess = model.new_int_var_from_domain(dominio, "Xadrez")
xadrez_var = model.new_optional_interval_var(Chess, 30, Chess + 30, chess_var, "Xadrez_Interval")
intervals.append(xadrez_var)

"TC Studying Optional Task"
study_var = model.new_bool_var("Stud_Presente")
boolean_variables.append(study_var)
StudyDomain = cp_model.Domain.FromIntervals([[minutesOfTheWeek(0, 10, 00), minutesOfTheWeek(0, 16, 00)]])
Study = model.new_int_var_from_domain(StudyDomain, "Estudar_TC")
StudyDuration = model.new_int_var(30, 120, "TC_Estudo")
StudyEndDuration = cp_model.Domain.FromIntervals([[minutesOfTheWeek(0, 10, 30), minutesOfTheWeek(0, 18, 00)]])
StudyEnd = model.new_int_var_from_domain(StudyEndDuration, "Estudar_TC_Fim")
model.add(Study + StudyDuration == StudyEnd)
Study_var = model.new_optional_interval_var(Study, StudyDuration, StudyEnd, study_var, "Estudar_Interval")
intervals.append(Study_var)

"Study In The Library"
library_var = model.new_bool_var("Library_Presente")
boolean_variables.append(library_var)
LibraryDomain = cp_model.Domain.FromIntervals([[minutesOfTheWeek(0, 10, 00), minutesOfTheWeek(0, 16, 00)]])
LibraryStart = model.new_int_var_from_domain(LibraryDomain, "Estudar_Biblioteca")
LibraryDuration = model.new_int_var(60, 180, "Estudar_Biblioteca")
LibraryEndDuration = cp_model.Domain.FromIntervals([[minutesOfTheWeek(0, 11, 00), minutesOfTheWeek(0, 19, 00)]])
LibraryEnd = model.new_int_var_from_domain(LibraryEndDuration, "Estudar_Bibliotca_Fim")
model.add(LibraryStart + LibraryDuration == LibraryEnd)
Library_var = model.new_optional_interval_var(LibraryStart, LibraryDuration, LibraryEnd, library_var, "Estudar_Biblioteca")
intervals.append(Library_var)"""

model.maximize(sum(bool_var * peso for bool_var,peso in zip(boolean_variables, pesos)))

model.add_no_overlap(intervals)

solver = cp_model.CpSolver()
status = solver.solve(model)

print(solver.Value(tasks["Gym"]["start"]))
print(solver.value(tasks["Gym"]["bool"]))
print(solver.Value(tasks["Chess"]["start"]))
print(solver.value(tasks["Chess"]["bool"]))
print(solver.Value(tasks["Study"]["start"]))
print(solver.value(tasks["Study"]["bool"]))
print(solver.value(tasks["Study"]["duration"]))
print(solver.value(tasks["Library"]["start"]))
print(solver.value(tasks["Library"]["bool"]))
print(solver.value(tasks["Library"]["duration"]))

print(solver.status_name(status))
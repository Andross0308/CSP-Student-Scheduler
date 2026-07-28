
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

tasks = [("Aula BD Pratica", ("Terça", "16:00"), ("Terça", "18:00"), minutesOfTheWeek(1, 16, 0) , minutesOfTheWeek(1,18,0)),
         ("Aula LAP Pratica", ("Terça", "14:00"), ("Terça", "16:00"), minutesOfTheWeek(1,14,0), minutesOfTheWeek(1,16,0)),
         ("Aula PED Pratica", ("Segunda", "10:00"), ("Segunda", "12:00"), minutesOfTheWeek(0,10,0), minutesOfTheWeek(0, 12,0)),
         ("Aula TC Pratica", ("Segunda", "8:00"), ("Segunda", "10:00"), minutesOfTheWeek(0,8,0), minutesOfTheWeek(0,10,0)),
         ("Aula BD Teorica", ("Quarta", "10:00"), ("Quarta", "11:30"), minutesOfTheWeek(2,10,0), minutesOfTheWeek(2,11,30)),
         ("Aula LAP Teorica", ("Quinta", "11:30"), ("Quinta", "13:00"), minutesOfTheWeek(3,11,30), minutesOfTheWeek(3,13,0)),
]

model = cp_model.CpModel()

#All time intervals that the model receives
intervalos = []
for nome,_,_, begin, end in tasks:
    duration = end - begin
    interval = model.new_interval_var(begin, duration,end, nome)
    intervalos.append(interval)

bool_var = model.new_bool_var("Ginasio_Presente")
ginasio_dominio = cp_model.Domain.FromIntervals([[minutesOfTheWeek(0,8,0), minutesOfTheWeek(0,21,0)],
                                                [minutesOfTheWeek(1,8,0), minutesOfTheWeek(1,21,0)],
                                                 [minutesOfTheWeek(2,8,0), minutesOfTheWeek(2,21,0)],
                                                 [minutesOfTheWeek(3,8,0), minutesOfTheWeek(3,21,0)],
                                                 [minutesOfTheWeek(4,8,0), minutesOfTheWeek(4,21,0)]])
Gym = model.new_int_var_from_domain(ginasio_dominio, "Ginasio")
gym_var = model.new_optional_interval_var(Gym, 60, Gym + 60, bool_var, "Ginasio_Interval")
intervalos.append(gym_var)

model.add_no_overlap(intervalos)

solver = cp_model.CpSolver()
status = solver.solve(model)

print(solver.Value(Gym))
print(solver.value(bool_var))

print(solver.status_name(status))
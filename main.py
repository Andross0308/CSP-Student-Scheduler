
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

def overlapTasks():
    for i in range(len(tasks)):
        for j in range(len(tasks)):
            if i == j: continue
            if tasks[i][4] > tasks[j][3] and tasks[j][4] > tasks[i][3]:
                print(tasks[i], tasks[j])
                print("error")
                return
    print("No overlaps")

overlapTasks()
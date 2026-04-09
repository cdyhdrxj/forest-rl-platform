
from services.patrol_planning.service.models import GridWorldTrainState

#Среднее время между появлением нарушителя и его перехватом/выходом
def calc_catch_latency(state: GridWorldTrainState):
    catch_arr = state.catch_latency
    return sum(catch_arr) / len(catch_arr) if catch_arr else 0.0
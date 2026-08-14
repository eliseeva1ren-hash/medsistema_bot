"""
Состояния анкеты записи на приём (aiogram FSM).
"""
from aiogram.fsm.state import State, StatesGroup


class Booking(StatesGroup):
    full_name = State()
    birth_date = State()
    phone = State()
    doctor = State()
    appointment_dt = State()
    confirm = State()

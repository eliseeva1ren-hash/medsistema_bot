"""
Состояния анкеты записи на приём (aiogram FSM).
"""
from aiogram.fsm.state import State, StatesGroup


class Booking(StatesGroup):
    full_name = State()
    birth_date = State()
    phone = State()
    direction = State()        # выбор направления (Шаг 4а)
    doctor = State()           # выбор специализации, если направление "Приём врачей" (Шаг 4б)
    custom_request = State()   # свободный текст для остальных направлений (Шаг 4б)
    appointment_dt = State()
    confirm = State()
    edit_choice = State()      # выбор поля для изменения из карточки подтверждения

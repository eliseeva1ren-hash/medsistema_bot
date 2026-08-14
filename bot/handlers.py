"""
Основная логика бота: приветствие, пошаговая анкета записи на приём,
подтверждение (с возможностью точечного изменения полей), отправка карточки
заявки администраторам и в Google Sheets.
"""
import logging

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot import config, keyboards as kb, validators as val, sheets
from bot.doctors import DIRECTIONS, SPECIALTIES
from bot.states import Booking

logger = logging.getLogger(__name__)
router = Router()


def _booking_card(data: dict, username: str, user_id: int) -> str:
    return (
        "🆕 <b>Новая заявка на приём</b>\n\n"
        f"👤 ФИО: {data['full_name']}\n"
        f"🎂 Дата рождения: {data['birth_date']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"🩺 Направление: {data['doctor_label']}\n"
        f"📅 Желаемая дата: {data['appointment_dt']}\n\n"
        f"💬 Telegram: @{username if username else '-'} (id {user_id})"
    )


def _confirm_summary(data: dict) -> str:
    return (
        "Проверьте данные заявки:\n\n"
        f"👤  {data['full_name']}\n"
        f"🎂  {data['birth_date']}\n"
        f"📞  {data['phone']}\n"
        f"🩺  {data['doctor_label']}\n"
        f"📅  {data['appointment_dt']}"
    )


async def _show_confirmation(message: Message, state: FSMContext):
    """Показывает карточку подтверждения и сбрасывает флаг 'редактируем поле'."""
    await state.update_data(editing=False)
    data = await state.get_data()
    await state.set_state(Booking.confirm)
    await message.answer(_confirm_summary(data), reply_markup=kb.confirm_keyboard())


# ---------- /start ----------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Здравствуйте! Вы в боте записи в клинику «Медсистема».\n\n"
        "Записаться на приём — просто: нажмите кнопку ниже и оставьте заявку. "
        "Это займёт около минуты 👇",
        reply_markup=kb.start_keyboard(),
    )


@router.callback_query(F.data == "start_booking")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Booking.full_name)
    await callback.message.answer(
        "Шаг 1 из 5.\nВведите, пожалуйста, ваше ФИО полностью (фамилия, имя, отчество)."
    )
    await callback.answer()


# ---------- Шаг 1: ФИО ----------

@router.message(Booking.full_name)
async def process_full_name(message: Message, state: FSMContext):
    ok, error, value = val.validate_full_name(message.text or "")
    if not ok:
        await message.answer(error)
        return
    await state.update_data(full_name=value)
    data = await state.get_data()
    if data.get("editing"):
        await _show_confirmation(message, state)
        return
    await state.set_state(Booking.birth_date)
    await message.answer("Шаг 2 из 5.\nВведите дату рождения в формате ДД.ММ.ГГГГ, например: 05.03.1990.")


# ---------- Шаг 2: дата рождения ----------

@router.message(Booking.birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    ok, error, value = val.validate_birth_date(message.text or "")
    if not ok:
        await message.answer(error)
        return
    await state.update_data(birth_date=value)
    data = await state.get_data()
    if data.get("editing"):
        await _show_confirmation(message, state)
        return
    await state.set_state(Booking.phone)
    await message.answer(
        "Шаг 3 из 5.\nУкажите номер телефона для связи (в формате +7XXXXXXXXXX) "
        "или нажмите кнопку ниже, чтобы отправить его автоматически.",
        reply_markup=kb.phone_keyboard(),
    )


# ---------- Шаг 3: телефон (текстом или кнопкой "поделиться контактом") ----------

@router.message(Booking.phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    ok, error, value = val.validate_phone(message.contact.phone_number)
    if not ok:
        await message.answer(error, reply_markup=kb.phone_keyboard())
        return
    await _save_phone(message, state, value)


@router.message(Booking.phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    ok, error, value = val.validate_phone(message.text or "")
    if not ok:
        await message.answer(error, reply_markup=kb.phone_keyboard())
        return
    await _save_phone(message, state, value)


async def _save_phone(message: Message, state: FSMContext, phone: str):
    await state.update_data(phone=phone)
    data = await state.get_data()
    if data.get("editing"):
        await message.answer("Телефон обновлён.", reply_markup=kb.remove_keyboard())
        await _show_confirmation(message, state)
        return
    await state.set_state(Booking.direction)
    await message.answer(
        "Шаг 4 из 5.\nВыберите направление:",
        reply_markup=kb.remove_keyboard(),
    )
    await message.answer("Выберите один из вариантов:", reply_markup=kb.directions_keyboard())


# ---------- Шаг 4а: направление ----------
# Кнопки направления остаются в чате и после выбора, поэтому разрешаем
# нажать другую кнопку "dir:" и позже — например, если клиент промахнулся
# и хочет выбрать направление заново (в т.ч. уже находясь на выборе врача,
# на свободном тексте или на шаге даты).

@router.callback_query(
    StateFilter(Booking.direction, Booking.doctor, Booking.custom_request, Booking.appointment_dt),
    F.data.startswith("dir:"),
)
async def process_direction(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":", 1)[1]
    label = DIRECTIONS.get(key)
    if not label:
        await callback.answer("Не удалось распознать выбор, попробуйте ещё раз.", show_alert=True)
        return
    await state.update_data(direction_key=key, direction_label=label)
    if key == "doctors":
        await state.set_state(Booking.doctor)
        await callback.message.answer("Выберите врача:", reply_markup=kb.specialties_keyboard())
    else:
        await state.set_state(Booking.custom_request)
        await callback.message.answer(
            f"«{label}» — напишите, что именно вас интересует 👇"
        )
    await callback.answer()


# ---------- Шаг 4б: специализация врача ----------
# Аналогично: даём переизбрать врача другой кнопкой, даже если клиент уже
# пошёл дальше и дошёл до шага даты.

@router.callback_query(
    StateFilter(Booking.doctor, Booking.appointment_dt),
    F.data.startswith("spec:"),
)
async def process_specialty(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":", 1)[1]
    label = SPECIALTIES.get(key)
    if not label:
        await callback.answer("Не удалось распознать выбор, попробуйте ещё раз.", show_alert=True)
        return
    await state.update_data(doctor_label=label)
    await _after_direction_chosen(callback.message, state)
    await callback.answer()


# ---------- Шаг 4б: свободный текст для остальных направлений ----------

@router.message(Booking.custom_request)
async def process_custom_request(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пожалуйста, опишите текстом, что нужно.")
        return
    data = await state.get_data()
    direction_label = data.get("direction_label", "Другое")
    await state.update_data(doctor_label=f"{direction_label}: {text}")
    await _after_direction_chosen(message, state)


async def _after_direction_chosen(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("editing"):
        await _show_confirmation(message, state)
        return
    await state.set_state(Booking.appointment_dt)
    await message.answer(
        "Шаг 5 из 5.\nУкажите желаемую дату приёма в формате ДД.ММ.ГГГГ, например: 20.08.2026.\n\n"
        "Уточним и подтвердим удобное время после обработки заявки."
    )


# ---------- Шаг 5: желаемая дата ----------

@router.message(Booking.appointment_dt)
async def process_appointment_date(message: Message, state: FSMContext):
    ok, error, value = val.validate_appointment_date(message.text or "")
    if not ok:
        await message.answer(error)
        return
    await state.update_data(appointment_dt=value)
    await _show_confirmation(message, state)


# ---------- Подтверждение ----------

@router.callback_query(Booking.confirm, F.data == "confirm_edit")
async def confirm_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Booking.edit_choice)
    await callback.message.answer("Что нужно изменить?", reply_markup=kb.edit_choice_keyboard())
    await callback.answer()


@router.callback_query(Booking.edit_choice, F.data == "edit_back")
async def edit_back(callback: CallbackQuery, state: FSMContext):
    await _show_confirmation(callback.message, state)
    await callback.answer()


@router.callback_query(Booking.edit_choice, F.data.startswith("edit:"))
async def edit_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":", 1)[1]
    await state.update_data(editing=True)
    if field == "full_name":
        await state.set_state(Booking.full_name)
        await callback.message.answer("Введите ФИО полностью (фамилия, имя, отчество).")
    elif field == "birth_date":
        await state.set_state(Booking.birth_date)
        await callback.message.answer("Введите дату рождения в формате ДД.ММ.ГГГГ, например: 05.03.1990.")
    elif field == "phone":
        await state.set_state(Booking.phone)
        await callback.message.answer(
            "Укажите номер телефона (в формате +7XXXXXXXXXX) или нажмите кнопку ниже.",
            reply_markup=kb.phone_keyboard(),
        )
    elif field == "direction":
        await state.set_state(Booking.direction)
        await callback.message.answer("Выберите направление:", reply_markup=kb.directions_keyboard())
    elif field == "appointment_dt":
        await state.set_state(Booking.appointment_dt)
        await callback.message.answer("Введите новую дату приёма в формате ДД.ММ.ГГГГ, например: 20.08.2026.")
    else:
        await callback.answer("Неизвестное поле.", show_alert=True)
        return
    await callback.answer()


@router.callback_query(Booking.confirm, F.data == "confirm_yes")
async def confirm_yes(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = callback.from_user
    card = _booking_card(data, user.username, user.id)

    # Отправляем карточку заявки обоим администраторам одновременно
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, card, parse_mode="HTML")
        except Exception:
            logger.exception("Не удалось отправить заявку администратору %s", admin_id)

    # Дублируем заявку в Google-таблицу (если подключена)
    sheets.append_booking(data, user.username, user.id)

    await callback.message.answer(
        "Спасибо! Ваша заявка принята ✅\nАдминистратор свяжется с вами для подтверждения записи."
    )
    await state.clear()
    await callback.answer()


# ---------- Фолбэк на случай сообщений вне сценария ----------

@router.message()
async def fallback(message: Message):
    await message.answer(
        "Чтобы записаться на приём, нажмите /start и следуйте подсказкам бота."
    )

"""
Основная логика бота: приветствие, пошаговая анкета записи на приём,
подтверждение, отправка карточки заявки администраторам и в Google Sheets.
"""
import logging

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot import config, keyboards as kb, validators as val, sheets
from bot.doctors import DOCTORS
from bot.states import Booking

logger = logging.getLogger(__name__)
router = Router()


def _booking_card(data: dict, username: str, user_id: int) -> str:
    return (
        "🆕 <b>Новая заявка на приём</b>\n\n"
        f"👤 ФИО: {data['full_name']}\n"
        f"🎂 Дата рождения: {data['birth_date']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"🩺 Врач/специализация: {data['doctor_label']}\n"
        f"🗓 Желаемая дата и время: {data['appointment_dt']}\n\n"
        f"💬 Telegram: @{username if username else '-'} (id {user_id})"
    )


# ---------- /start ----------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Здравствуйте! Это бот записи на приём в «{config.CLINIC_NAME}».\n\n"
        f"📍 {config.CLINIC_ADDRESS}\n"
        f"📞 {config.CLINIC_PHONE}\n"
        f"🕐 {config.CLINIC_HOURS}\n\n"
        "Нажмите кнопку ниже, чтобы оставить заявку — это займёт около минуты.",
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
    await _save_phone_and_ask_doctor(message, state, value)


@router.message(Booking.phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    ok, error, value = val.validate_phone(message.text or "")
    if not ok:
        await message.answer(error, reply_markup=kb.phone_keyboard())
        return
    await _save_phone_and_ask_doctor(message, state, value)


async def _save_phone_and_ask_doctor(message: Message, state: FSMContext, phone: str):
    await state.update_data(phone=phone)
    await state.set_state(Booking.doctor)
    await message.answer(
        "Шаг 4 из 5.\nВыберите врача или специализацию:",
        reply_markup=kb.remove_keyboard(),
    )
    await message.answer("Выберите один из вариантов:", reply_markup=kb.doctors_keyboard())


# ---------- Шаг 4: врач/специализация ----------

@router.callback_query(Booking.doctor, F.data.startswith("doc:"))
async def process_doctor(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":", 1)[1]
    label = DOCTORS.get(key)
    if not label:
        await callback.answer("Не удалось распознать выбор, попробуйте ещё раз.", show_alert=True)
        return
    await state.update_data(doctor_key=key, doctor_label=label)
    await state.set_state(Booking.appointment_dt)
    await callback.message.answer(
        "Шаг 5 из 5.\nУкажите желаемую дату и время приёма в формате ДД.ММ.ГГГГ ЧЧ:ММ, "
        "например: 20.08.2026 14:30.\n\nТочное время мы подтвердим дополнительно после обработки заявки."
    )
    await callback.answer()


# ---------- Шаг 5: желаемые дата и время ----------

@router.message(Booking.appointment_dt)
async def process_appointment_dt(message: Message, state: FSMContext):
    ok, error, value = val.validate_appointment_dt(message.text or "")
    if not ok:
        await message.answer(error)
        return
    await state.update_data(appointment_dt=value)
    data = await state.get_data()
    await state.set_state(Booking.confirm)
    summary = (
        "Проверьте, пожалуйста, данные заявки:\n\n"
        f"👤 ФИО: {data['full_name']}\n"
        f"🎂 Дата рождения: {data['birth_date']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"🩺 Врач: {data['doctor_label']}\n"
        f"🗓 Желаемые дата и время: {data['appointment_dt']}"
    )
    await message.answer(summary, reply_markup=kb.confirm_keyboard())


# ---------- Подтверждение ----------

@router.callback_query(Booking.confirm, F.data == "confirm_restart")
async def confirm_restart(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Booking.full_name)
    await callback.message.answer("Хорошо, начнём заново.\n\nШаг 1 из 5.\nВведите, пожалуйста, ваше ФИО полностью.")
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

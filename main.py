import pandas as pd
import datetime
import logging
import os
from telegram import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext

# Настройки Telegram бота
TOKEN = '7539124014:AAGekjZrKUuBCP8-f1nP_aKo_RgO8aNhwXg'
CHAT_ID = '-4509208587'
ALLOWED_USERS = [376492213]  # Замените на реальные идентификаторы пользователей

# Создаем объект бота
bot = Bot(token=TOKEN)

# Чтение Excel файла и преобразование столбца в формат datetime
df = pd.read_excel('ecp_expiry_dates.xlsx')
df['Дата окончания ЭЦП'] = pd.to_datetime(df['Дата окончания ЭЦП'], format='%d.%m.%Y', errors='coerce')

# Текущая дата
today = datetime.datetime.today()

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Файл для хранения дат отправленных уведомлений
notified_dates_file = 'notified_dates.txt'

def is_user_allowed(update):
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    return user_id in ALLOWED_USERS

def restricted(func):
    def wrapped(update, context, *args, **kwargs):
        if not is_user_allowed(update):
            update.message.reply_text("Вам не разрешено использовать этого бота.") if update.message else update.callback_query.message.reply_text("Вам не разрешено использовать этого бота.")
            return
        return func(update, context, *args, **kwargs)
    return wrapped

def add_ecp_start(update, context):
    update.message.reply_text("Введите данные в формате: 'Организация-владелец, ФИО владельца, Дата окончания (ДД.ММ.ГГГГ)'")
    context.user_data['expecting'] = 'add_ecp'

def add_ecp(update, context):
    if 'expecting' in context.user_data and context.user_data['expecting'] == 'add_ecp':
        try:
            text = update.message.text
            org_name, owner_name, expiry_date_str = text.split(',')
            expiry_date = datetime.datetime.strptime(expiry_date_str.strip(), '%d.%m.%Y')
            new_row = pd.DataFrame([[org_name.strip(), owner_name.strip(), expiry_date]], columns=['Организация-владелец', 'ФИО владельца', 'Дата окончания ЭЦП'])
            global df
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_excel('ecp_expiry_dates.xlsx', index=False)
            update.message.reply_text(f"Запись '{org_name.strip()}' с датой окончания {expiry_date_str.strip()} добавлена.")
            context.user_data['expecting'] = None
        except Exception as e:
            update.message.reply_text("Произошла ошибка при добавлении записи. Убедитесь, что формат данных правильный.")
    elif 'expecting' in context.user_data and context.user_data['expecting'] == 'delete_ecp':
        delete_ecp(update, context)

def delete_ecp_start(update, context):
    update.message.reply_text("Введите имя организации, которая нужно удалить:")
    context.user_data['expecting'] = 'delete_ecp'

def delete_ecp(update, context):
    if 'expecting' in context.user_data and context.user_data['expecting'] == 'delete_ecp':
        org_name = update.message.text.strip()
        global df
        if org_name in df['Организация-владелец'].values:
            df = df[df['Организация-владелец'] != org_name]
            df.to_excel('ecp_expiry_dates.xlsx', index=False)
            update.message.reply_text(f"Запись '{org_name}' удалена.")
            context.user_data['expecting'] = None
        else:
            update.message.reply_text(f"Запись '{org_name}' не найдена.")
            context.user_data['expecting'] = None

@restricted
def button(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'this_month':
        check_expiring_ecp(query, context, month_offset=0)
    elif query.data == 'next_month':
        check_expiring_ecp(query, context, month_offset=1)
    elif query.data == 'last_three_months':
        check_expiring_ecp(query, context, month_offset=3)

@restricted
def check_expiring_ecp(update, context, month_offset=0):
    now = datetime.datetime.now()
    month_start = datetime.datetime(now.year, now.month + month_offset, 1)
    next_month_start = datetime.datetime(now.year, now.month + month_offset + 1, 1)

    expiring_ecp = df[(df['Дата окончания ЭЦП'] >= month_start) & (df['Дата окончания ЭЦП'] < next_month_start)]

    if expiring_ecp.empty:
        update.message.reply_text('Нет ЭЦП, истекающих в выбранный период.') if update.message else update.callback_query.message.reply_text('Нет ЭЦП, истекающих в выбранный период.')
    else:
        messages = []
        for index, row in expiring_ecp.iterrows():
            org_name = row['Организация-владелец']
            owner_name = row['ФИО владельца']
            expiry_date = row['Дата окончания ЭЦП']
            days_left = (expiry_date - today).days
            message = f'{org_name} ({owner_name}) - ЭЦП истекает {expiry_date.strftime("%d.%m.%Y")} ({days_left} дней осталось)'
            messages.append(message)
        try:
            bot.send_message(chat_id=CHAT_ID, text='\n\n'.join(messages), timeout=120)
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")

@restricted
def check_expiring_ecp_three_months(update, context):
    now = datetime.datetime.now()
    three_months_later = now + datetime.timedelta(days=90)
    expiring_ecp = df[(df['Дата окончания ЭЦП'] >= now) & (df['Дата окончания ЭЦП'] <= three_months_later)]

    if expiring_ecp.empty:
        update.message.reply_text('Нет ЭЦП, истекающих в ближайшие 3 месяца.') if update.message else update.callback_query.message.reply_text('Нет ЭЦП, истекающих в ближайшие 3 месяца.')
    else:
        messages = []
        for index, row in expiring_ecp.iterrows():
            org_name = row['Организация-владелец']
            owner_name = row['ФИО владельца']
            expiry_date = row['Дата окончания ЭЦП']
            days_left = (expiry_date - today).days
            message = f'{org_name} ({owner_name}) - ЭЦП истекает {expiry_date.strftime("%d.%m.%Y")} ({days_left} дней осталось)'
            messages.append(message)
        try:
            bot.send_message(chat_id=CHAT_ID, text='\n\n'.join(messages), timeout=120)
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")

def check_expiry(context: CallbackContext):
    global today
    today = datetime.datetime.today()
    notified_dates = load_notified_dates()

    messages = []
    for index, row in df.iterrows():
        org_name = row['Организация-владелец']
        owner_name = row['ФИО владельца']
        expiry_date = row['Дата окончания ЭЦП']

        if isinstance(expiry_date, pd.Timestamp):
            expiry_date = expiry_date.to_pydatetime()

        days_left = (expiry_date - today).days

        if days_left <= 56 and expiry_date not in notified_dates:
            message = f'Уведомление: {org_name} ({owner_name}) - ЭЦП истекает через {days_left} дней ({expiry_date.strftime("%d.%m.%Y")})'
            messages.append(message)
            notified_dates.append(expiry_date)

    if messages:
        try:
            bot.send_message(chat_id=CHAT_ID, text='\n\n'.join(messages), timeout=120)
            save_notified_dates(notified_dates)
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")

def load_notified_dates():
    if os.path.exists(notified_dates_file):
        with open(notified_dates_file, 'r') as f:
            dates = f.read().splitlines()
            return [datetime.datetime.strptime(date, '%Y-%m-%d') for date in dates]
    return []

def save_notified_dates(dates):
    with open(notified_dates_file, 'w') as f:
        for date in dates:
            f.write(date.strftime('%Y-%m-%d') + '\n')

def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")

# Настройка команд и кнопок
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher
dispatcher.add_handler(CommandHandler('ecp_this_month', lambda update, context: check_expiring_ecp(update, context, month_offset=0)))
dispatcher.add_handler(CommandHandler('ecp_next_month', lambda update, context: check_expiring_ecp(update, context, month_offset=1)))
dispatcher.add_handler(CommandHandler('last_three_months_ecp', check_expiring_ecp_three_months))
dispatcher.add_handler(CommandHandler('add_ecp', add_ecp_start))
dispatcher.add_handler(CommandHandler('delete_ecp', delete_ecp_start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, add_ecp))
dispatcher.add_handler(CallbackQueryHandler(button))
dispatcher.add_error_handler(error_handler)

# Настройка планировщика
job_queue = updater.job_queue
job_queue.run_daily(check_expiry, time=datetime.time(hour=8, minute=0))

# Запуск бота
if __name__ == '__main__':
    updater.start_polling()
    updater.idle()

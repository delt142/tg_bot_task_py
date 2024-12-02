from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = 'Your api'

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Task(StatesGroup):
    waiting_for_title = State()
    waiting_for_task_items = State()
    waiting_for_deadline = State()
    waiting_for_new_title = State()
    waiting_for_new_task_item = State()
    waiting_for_priority_change = State()

tasks = {}
task_list = []

# Кнопки главного меню
main_menu_buttons = [
    KeyboardButton('Создать задание'),
    KeyboardButton('Выбрать из существующих')
]
main_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(*main_menu_buttons)

@dp.message_handler(commands='start')
async def start(message: types.Message):
    await message.answer("Добро пожаловать в Task Manager! Выберите действие:", reply_markup=main_menu)

@dp.message_handler(lambda message: message.text == 'Создать задание')
async def create_task(message: types.Message):
    await message.answer("Введите тему задания:")
    await Task.waiting_for_title.set()

@dp.message_handler(state=Task.waiting_for_title)
async def enter_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите пункты задания по одному. Введите 'готово' для завершения.")
    await Task.waiting_for_task_items.set()

@dp.message_handler(state=Task.waiting_for_task_items)
async def enter_task_items(message: types.Message, state: FSMContext):
    if message.text.lower() == 'готово':
        await message.answer("Введите дату выполнения (формат: ГГГГ-ММ-ДД). Если не хотите указывать дату, отправьте 'нет'.")
        await Task.waiting_for_deadline.set()
    else:
        task_list.append(message.text)
        await message.answer("Пункт добавлен. Введите следующий пункт или 'готово' для завершения.")

@dp.message_handler(state=Task.waiting_for_deadline)
async def enter_deadline(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    title = user_data['title']
    deadline = message.text if message.text.lower() != 'нет' else None
    tasks[title] = {'items': task_list.copy(), 'deadline': deadline, 'completed': [], 'priority': 0}
    task_list.clear()
    await state.finish()
    await message.answer("Задание создано!", reply_markup=main_menu)

@dp.message_handler(lambda message: message.text == 'Выбрать из существующих')
async def choose_task(message: types.Message):
    if tasks:
        task_buttons = [InlineKeyboardButton(text=title, callback_data=title) for title in tasks.keys()]
        task_menu = InlineKeyboardMarkup(row_width=1).add(*task_buttons)
        await message.answer("Выберите тему задания:", reply_markup=task_menu)
    else:
        await message.answer("Нет существующих заданий.", reply_markup=main_menu)

@dp.callback_query_handler(lambda call: call.data in tasks.keys())
async def select_task(call: types.CallbackQuery):
    title = call.data
    task = tasks[title]
    task_text = '\n'.join([f"- [ ] {item}" for item in task['items']])
    await call.message.answer(f"Задание: {title}\n\n{task_text}", reply_markup=task_management_menu(title))
    await call.answer()

def task_management_menu(title):
    buttons = [
        InlineKeyboardButton(text="Переименовать тему", callback_data=f"rename_{title}"),
        InlineKeyboardButton(text="Добавить пункт", callback_data=f"add_{title}"),
        InlineKeyboardButton(text="Изменить приоритет", callback_data=f"priority_{title}"),
        InlineKeyboardButton(text="Удалить тему", callback_data=f"delete_{title}")
    ]
    return InlineKeyboardMarkup(row_width=1).add(*buttons)

@dp.callback_query_handler(lambda call: call.data.startswith('rename_'))
async def rename_task(call: types.CallbackQuery):
    title = call.data.split('rename_')[1]
    await call.message.answer(f"Введите новое название для темы '{title}':")
    await Task.waiting_for_new_title.set()
    await call.answer()

@dp.message_handler(state=Task.waiting_for_new_title)
async def set_new_title(message: types.Message, state: FSMContext):
    new_title = message.text
    old_title = list(tasks.keys())[0]
    tasks[new_title] = tasks.pop(old_title)
    await state.finish()
    await message.answer(f"Тема '{old_title}' переименована в '{new_title}'.", reply_markup=main_menu)

@dp.callback_query_handler(lambda call: call.data.startswith('add_'))
async def add_task_item(call: types.CallbackQuery):
    title = call.data.split('add_')[1]
    await call.message.answer(f"Введите новый пункт для темы '{title}':")
    await Task.waiting_for_new_task_item.set()
    await call.answer()

@dp.message_handler(state=Task.waiting_for_new_task_item)
async def set_new_task_item(message: types.Message, state: FSMContext):
    new_item = message.text
    title = list(tasks.keys())[0]
    tasks[title]['items'].append(new_item)
    await state.finish()
    await message.answer(f"Пункт добавлен в тему '{title}'.", reply_markup=main_menu)

@dp.callback_query_handler(lambda call: call.data.startswith('priority_'))
async def change_task_priority(call: types.CallbackQuery):
    title = call.data.split('priority_')[1]
    await call.message.answer(f"Установите новый приоритет для темы '{title}' (0 - низкий, 1 - средний, 2 - высокий):")
    await Task.waiting_for_priority_change.set()
    await call.answer()

@dp.message_handler(state=Task.waiting_for_priority_change)
async def set_task_priority(message: types.Message, state: FSMContext):
    priority = int(message.text)
    title = list(tasks.keys())[0]
    tasks[title]['priority'] = priority
    await state.finish()
    await message.answer(f"Приоритет для темы '{title}' установлен на {priority}.", reply_markup=main_menu)

@dp.callback_query_handler(lambda call: call.data.startswith('delete_'))
async def confirm_delete_task(call: types.CallbackQuery):
    title = call.data.split('delete_')[1]
    tasks.pop(title, None)
    await call.message.answer(f"Тема '{title}' удалена.", reply_markup=main_menu)
    await call.answer()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

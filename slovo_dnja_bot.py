import telegram
from telegram import  Poll, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
import random
import json

from telegram.ext import (
	Updater,
	CommandHandler,
	MessageHandler,
	Filters,
	PollAnswerHandler,
	PollHandler,
	ConversationHandler,
	CallbackContext
)


import logging
import sqlite3
import re


# logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


logger = logging.getLogger(__name__)

TAG, ANSWER, MORE = range(3)


# extract random facts from the database
def random_fact(tag: str):
	connection = sqlite3.connect('facts.db')
	cursor = connection.cursor()
	cursor.execute('SELECT * FROM tags WHERE tag=?', (tag,))
	tag_id = cursor.fetchall()[0][0]
	cursor.execute('SELECT * FROM facts_to_tags WHERE tag_id=?', (tag_id,))
	tags = cursor.fetchall()

	all_facts = []
	for tag in tags:
		cursor.execute('SELECT * FROM facts WHERE fact_id=?', (tag[1],))
		all_facts.append(cursor.fetchall()[0])
		fact = random.choice(all_facts)

	answer = [fact[2], fact[3], fact[4], fact[5]]
	question = fact[1]
	answers = []
	for k in answer:
		if k != '-':
			answers.append(k)

	right_answer = fact[6]

	rand_fact = fact[7]
	if len(answers) == 2:
		#reply_keyboard = [['1', '2']]
		question = question + '\n\n' + '1. ' + answers[0] + '\n' + '2. ' + answers[1]
	elif len(answers) == 3:
		#reply_keyboard = [['1', '2', '3']]
		question = question + '\n\n' + '1. ' + answers[0] + '\n' + '2. ' + answers[1] + '\n' + '3. ' + answers[2]
	elif len(answers) == 4:
		#reply_keyboard = [['1', '2'], ['3', '4']]
		question = question + '\n\n' + '1. ' + answers[0] + '\n' + '2. ' + answers[1] + '\n' \
				   + '3. ' + answers[2] + '\n' + '4. ' + answers[3]
	source = fact[8]

	return question, right_answer, rand_fact, source


# function for starting conversation
def start(update: Update, context: CallbackContext) -> int:
	reply_keyboard = [['орфография', 'орфоэпия', 'морфология'],
					  ['сленг', 'заимствования', 'типология'],
					  ['РКИ', 'школьные_правила', 'этимология'],
					  ['семантика', 'лексика', 'фонетика'],
					  ['социолингвистика', 'синтаксис']]

	update.message.reply_text(
		'Привет! Выбери, интересный факт из какого раздела ты бы хотел_а получить! Подробнее о боте по команде /help.',
		reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
	)

	return TAG


def tag(update: Update, context: CallbackContext) -> int:
	user_tag = update.message.text
	question, right_answer, rand_fact, source = random_fact(user_tag)
	context.user_data["question"] = question
	context.user_data["right_answer"] = right_answer
	context.user_data["fact"] = rand_fact
	context.user_data["source"] = source

	update.message.reply_text(context.user_data["question"])

	return ANSWER


def answer(update: Update, context: CallbackContext) -> int:
	text = update.message.text
	if text in context.user_data["right_answer"]:
		if int(text) == int(context.user_data["right_answer"]):
			is_right = 'Это правильный ответ!'
		else:
			is_right = f'Почти верно, правильным ответом является {context.user_data["right_answer"]}!'
	else:
		is_right = f'Нет, на самом деле правильным ответом является {context.user_data["right_answer"]}!'

	if context.user_data["source"] is None:
		context.user_data["source"] = ''
	else:
		context.user_data["source"] = '\n\n' + 'Источник: ' + context.user_data["source"]

	full_text = is_right + '\n' + context.user_data["fact"] + context.user_data["source"]
	update.message.reply_text(full_text)

	reply_keyboard = [['/start', '/end', '/help']]
	text = 'Если ты хочешь получить еще один факт, выбери команду start, если хочешь закончить - выбери команду end.\
			Подробнее о боте - команда help. '
	update.message.reply_text(
		text,
		reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
	)
	return MORE


def end(update: Update, context: CallbackContext) -> int:
	update.message.reply_text(
		'Хорошо! До скорых встреч!'
	)
	return ConversationHandler.END


# help command that returns description of the bot
def help(update: Update, context: CallbackContext):
	text = "Бот, который случайным образом выдаёт пользователю интересные факты русского языка.\n\
	Семантика - факты, который поясняют особенности значений слов или выражений.\n\
	Орфография - факты, связанные с орфографией современного русского языка\
	 (Почему некоторые слова пишутся так, а не иначе?).\n\
	Школьные правила - факты, которые объясняют некоторые правила русского языка, изучаемые в школе.\n\
	Лексика - факты, связанные с особенностями употребления некоторых слов или выражений.\n\
	Морфология - факты, которые объясняют особые формы слов или их морфем.\n\
	Социолингвистика - факты, связанные с социальной природой языка.\n\
	Синтаксис - факты, которые поясняют правила соединения слов в предложения.\n\
	Фонетика - факты, связанные с особенностями звукового строя русского языка.\n\
	Сленг - факты, которые описывают слова и конструкции, характерные для разговорной речи.\
	Эта категория отчасти пересекается с заимствованиями, поскольку в русском сленге много слов,\
	 пришедших из других языков (например, из английского).\n\n\
	*Доступные команды:*\n\
	/start запустить бота\n\
	/end остановить бота"
	context.bot.send_message(chat_id=update.effective_chat.id,  parse_mode = 'Markdown', text=text)


# function that replies to messages that bot doesn't understand
def unknown(update, context):
	context.bot.send_message(chat_id=update.effective_chat.id, text="Прости, я не понимаю, что ты говоришь")


# logging errors
def error(update, context):
	logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
	""" Run bot """

	updater = Updater(token='', use_context=True)
	dispatcher = updater.dispatcher

	conv_handler = ConversationHandler(
		entry_points=[CommandHandler('start', start)],
		states={
			TAG: [MessageHandler(Filters.regex('^(орфография|орфоэпия|морфология|сленг|заимствования|типология|РКИ|школьные_правила|этимология|семантика|социолингвистика|синтаксис|лексика|фонетика)$'), tag)],
			ANSWER: [MessageHandler(Filters.regex('^(1|2|3|4)+$'), answer)],
			MORE: [
				CommandHandler('start', start),
				CommandHandler('end', end),
				CommandHandler('help', help)
			],
		},
		fallbacks=[CommandHandler('cancel', end),
				   CommandHandler('help', help)],
	)
	dispatcher.add_handler(conv_handler)

	# log all errors
	dispatcher.add_error_handler(error)

	updater.start_polling()

	updater.idle()


if __name__ == '__main__':
	main()

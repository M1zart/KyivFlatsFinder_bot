import os
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from anthropic import Anthropic

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

client = Anthropic(api_key=ANTHROPIC_API_KEY)

FLATS_SYSTEM_PROMPT = """Ты — помощник по поиску недвижимости в Киеве.

ПОСТОЯННЫЕ КРИТЕРИИ ПОИСКА:
- Город: Киев
- Районы: центральные и престижные (Шевченковский, Печерский, 
  Голосеевский, Подольский, Соломенский) — НЕ окраины и спальные 
  районы (Троещина, Борщаговка, Виноградарь и аналогичные)
- Площадь: 40-50 м²
- Тип: вторичный рынок, с ремонтом
- Год постройки дома: от 2015
- Контакт: только от собственника, без риэлторов/агентств

ПЕРЕМЕННЫЙ КРИТЕРИЙ — БЮДЖЕТ:
Указывается в запросе пользователя (максимальная цена в USD).

ИСТОЧНИКИ ДЛЯ ПОИСКА (используй web search по каждому):
1. dom.ria.com
2. olx.ua
3. flatfy.ua
4. 100realty.ua
5. lun.ua
6. aviso.ua

ЗАДАЧА:
Найди актуальные объявления, соответствующие всем критериям. 
Для каждого подходящего варианта укажи:
- Источник
- Район
- Площадь, этаж
- Год постройки (если указан)
- Цена
- Краткое описание (1 предложение)
- Ссылка на объявление

ПРАВИЛА:
- Только объявления от собственников (если указано "от риэлтора" 
  или "агентство" — пропускай)
- Если на каком-то сайте подходящих вариантов не нашлось — 
  укажи это прямо, не выдумывай
- Отсортируй результаты по цене (от дешёвых к дорогим)
- В конце — краткий вывод: сколько всего найдено вариантов, 
  какой ценовой диапазон реально доступен по этим критериям
- Без markdown-разметки (*, #, _, >) — обычный текст для Telegram
- Не выдумывай объявления, цены или ссылки — используй только 
  то, что нашёл через поиск"""


def clean_markdown(text: str) -> str:
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^-{3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    text = text.replace("**", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def flats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Формат: /flats [бюджет в USD], например /flats 80000"
        )
        return

    budget = " ".join(context.args)
    await update.message.reply_text("Ищу варианты, минута...")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=FLATS_SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": f"Бюджет: до {budget} USD"}],
    )

    text_parts = [block.text for block in response.content if block.type == "text"]
    result = "\n".join(text_parts)
    result = clean_markdown(result)

    await update.message.reply_text(result)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("flats", flats_command))
    app.run_polling()


if __name__ == "__main__":
    main()

# 🐍 Scraping Python – Padel Court Notifier

**Scraping Python** is a small automation script that checks for available padel court reservations from a government-run booking system and sends alerts via Telegram when your desired time slot is free.

It was my first project built entirely in Python and my first integration with the Telegram Bot API.

---

## ✨ Features

- 📆 **Time Slot Monitoring** – Checks for available reservations in a public padel court system.
- 📩 **Telegram Integration** – Sends messages when your preferred time becomes available.
- 🔁 **Scheduled Execution** – Can be triggered periodically using cron or similar schedulers.

---

## 🛠️ Tech Stack

- **Python**
- **Selenium** – for browser automation
- **BeautifulSoup** – for HTML parsing
- **Telegram Bot API**

---

## ⚙️ How to Use

1. Clone the repository:

```bash
git clone https://github.com/TomasAgustinDuro/Scrapping-python.git
cd Scrapping-python
```
2. Install dependencies and set up your environment:
```bash
pip install -r requirements.txt

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TARGET_HOUR=19:00

python scraper.py
```

## 📈 What I learned

- Web scraping techniques using Python and Selenium.

- Handling dynamic content and login-based sites.

- Integrating Telegram for automated user alerts.

- Working with environment variables for secrets and configuration.

## 🤝 How to contribute

Contributions are welcome! You can help by:

- 🐞 Reporting bugs or edge cases
- 🔧 Improving scraping efficiency or Telegram messaging logic
- 💡 Suggesting enhancements or reusable patterns

## 🙋‍♂️ Author

This project was built to support a local entrepreneur —  
developed by [Tomás Duro](https://tommasdev.vercel.app), with love from Buenos Aires 🇦🇷

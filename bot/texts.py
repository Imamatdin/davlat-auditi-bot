"""User-facing strings in Uzbek (Latin script).

All copy lives here so a non-developer can edit wording without touching logic.
No em dashes anywhere: use commas, colons, or pipes instead.
"""

# ---------------------------------------------------------------------------
# Welcome / start
# ---------------------------------------------------------------------------

WELCOME = (
    "Assalomu alaykum, hurmatli abituriyent!\n\n"
    "<b>Davlat Auditi Oliy Maktabi</b>ga xush kelibsiz.\n"
    "Toshkent Davlat Iqtisodiyot Universiteti tarkibida faoliyat yuritadi.\n\n"
    "Oliy Maktab O'zbekiston Respublikasi Prezidentining "
    "PF-252-son Farmoni asosida tashkil etilgan.\n\n"
    "Dunyoda ikkita: biri Xitoyda, biri O'zbekistonda.\n\n"
    "<b>2026/2027 o'quv yili uchun qabul:</b>\n"
    "Bakalavriat: 200 o'rin\n"
    "Magistratura: 30 o'rin\n\n"
    "Ro'yxatdan o'tish uchun quyidagi tugmani bosing."
)

WELCOME_REGISTERED = (
    "Assalomu alaykum, <b>{name}</b>!\n\n"
    "Siz allaqachon ro'yxatdan o'tgansiz.\n\n"
    "Endi siz istalgan vaqtda savol yozib yuborishingiz mumkin: "
    "oddiy matn yoki ovozli xabar shaklida. Javob administrator "
    "tomonidan iloji boricha tezroq yuboriladi.\n\n"
    "/info, ma'lumotlaringizni ko'rish uchun\n"
    "/start, qaytadan ro'yxatdan o'tish uchun"
)

# ---------------------------------------------------------------------------
# Buttons (reply / inline)
# ---------------------------------------------------------------------------

BTN_REGISTER = "Ro'yxatdan o'tish"
BTN_REREGISTER = "Qaytadan ro'yxatdan o'tish"
BTN_SHARE_CONTACT = "Telefon raqamni yuborish"
BTN_BAKALAVR = "Bakalavriat (200 o'rin)"
BTN_MAGISTRATURA = "Magistratura (30 o'rin)"
BTN_CONFIRM = "Tasdiqlash"
BTN_RESTART = "Qaytadan"
BTN_CANCEL = "Bekor qilish"
BTN_REPLY = "Javob yozish"

# ---------------------------------------------------------------------------
# Registration FSM prompts
# ---------------------------------------------------------------------------

ASK_NAME = (
    "Iltimos, <b>ism va familiyangizni</b> to'liq yozing.\n\n"
    "Masalan: Aliyev Olim Akmalovich"
)
ERR_NAME_SHORT = (
    "Ism juda qisqa ko'rinmoqda. Iltimos, ism va familiyangizni "
    "to'liq, kamida 3 ta harfdan iborat qilib yozing."
)
ERR_NAME_INVALID = (
    "Iltimos, faqat harf, bo'sh joy va apostrof (') belgilaridan foydalaning. "
    "Raqam va boshqa belgilarni qo'shmang."
)

ASK_PHONE = (
    "Endi <b>telefon raqamingizni</b> yuboring.\n\n"
    "Quyidagi tugma orqali yuborishingiz yoki qo'lda yozishingiz mumkin.\n"
    "Masalan: +998901234567"
)
ERR_PHONE_INVALID = (
    "Telefon raqam noto'g'ri formatda. Iltimos, quyidagi ko'rinishda yuboring:\n"
    "+998901234567, 998901234567 yoki 901234567"
)

ASK_PROGRAM = (
    "<b>Yo'nalishni</b> tanlang:\n\n"
    "Bakalavriat: 4 yillik to'liq oliy ta'lim, 200 o'rin\n"
    "Magistratura: 2 yillik magistr darajasi, 30 o'rin"
)

ASK_REGION = (
    "Yashash <b>viloyatingiz yoki shahringizni</b> yozing.\n\n"
    "Masalan: Toshkent shahri, Samarqand viloyati"
)
ERR_REGION_SHORT = (
    "Viloyat yoki shahar nomi juda qisqa. Iltimos, to'liq yozing."
)

CONFIRM_TITLE = "<b>Ma'lumotlaringizni tekshiring:</b>\n\n"
CONFIRM_TEMPLATE = (
    "{title}"
    "Ism familiya: <b>{name}</b>\n"
    "Telefon: <b>{phone}</b>\n"
    "Yo'nalish: <b>{program}</b>\n"
    "Viloyat / shahar: <b>{region}</b>\n\n"
    "Hammasi to'g'rimi?"
)

REG_SUCCESS = (
    "Tabriklaymiz, <b>{name}</b>!\n"
    "Siz Davlat Auditi Oliy Maktabi ro'yxatiga muvaffaqiyatli qo'shildingiz.\n\n"
    "Endi siz istalgan vaqtda savol yozib yuborishingiz mumkin: "
    "oddiy matn yoki ovozli xabar shaklida. Administrator javob beradi.\n\n"
    "/info, ma'lumotlaringizni ko'rish uchun"
)

REG_RESTARTED = "Yaxshi, ro'yxatdan o'tishni qaytadan boshlaymiz."
REG_CANCELLED = "Ro'yxatdan o'tish bekor qilindi. Boshlash uchun /start ni bosing."

# ---------------------------------------------------------------------------
# /info
# ---------------------------------------------------------------------------

INFO_TEMPLATE = (
    "<b>Sizning ma'lumotlaringiz:</b>\n\n"
    "Ism familiya: <b>{name}</b>\n"
    "Telefon: <b>{phone}</b>\n"
    "Yo'nalish: <b>{program}</b>\n"
    "Viloyat / shahar: <b>{region}</b>\n"
    "Ro'yxatdan o'tgan vaqt: <b>{registered_at}</b>\n\n"
    "Ma'lumotlarni o'zgartirish uchun /start ni bosing."
)
INFO_NOT_REGISTERED = (
    "Siz hali ro'yxatdan o'tmagansiz. Boshlash uchun /start ni bosing."
)

# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

NEED_REGISTRATION = (
    "Savol yuborish uchun avval ro'yxatdan o'tishingiz kerak.\n"
    "Boshlash uchun /start ni bosing."
)
QUESTION_RECEIVED_TEXT = (
    "Savolingiz qabul qilindi. Administrator javob bergach, sizga xabar yuboramiz."
)
QUESTION_RECEIVED_VOICE = (
    "Ovozli xabaringiz qabul qilindi. Administrator javob bergach, sizga xabar yuboramiz."
)
UNSUPPORTED_MESSAGE = (
    "Faqat matn yoki ovozli xabar yuborishingiz mumkin."
)

# ---------------------------------------------------------------------------
# Admin notifications
# ---------------------------------------------------------------------------

ADMIN_NEW_REGISTRATION = (
    "<b>Yangi ro'yxat #{count}</b>\n\n"
    "Ism familiya: <b>{name}</b>\n"
    "Telefon: <code>{phone}</code>\n"
    "Yo'nalish: <b>{program}</b>\n"
    "Viloyat / shahar: <b>{region}</b>\n"
    "Telegram: @{username} (ID: <code>{user_id}</code>)\n"
    "Vaqt: {registered_at}"
)

ADMIN_NEW_QUESTION_HEADER = (
    "<b>Yangi savol #{qid}</b>\n\n"
    "<b>{name}</b> ({program})\n"
    "Telefon: <code>{phone}</code>\n"
    "Telegram: @{username} (ID: <code>{user_id}</code>)\n"
)
ADMIN_NEW_QUESTION_TEXT = ADMIN_NEW_QUESTION_HEADER + "\nSavol:\n{text}"
ADMIN_NEW_QUESTION_VOICE = ADMIN_NEW_QUESTION_HEADER + "\nOvozli savol quyida:"

# ---------------------------------------------------------------------------
# Admin dashboard / commands
# ---------------------------------------------------------------------------

ADMIN_DASHBOARD = (
    "<b>Administrator paneli</b>\n\n"
    "Jami ro'yxatdan o'tganlar: <b>{total}</b>\n"
    "Bakalavriat: <b>{bakalavr}</b> / 200\n"
    "Magistratura: <b>{magistr}</b> / 30\n\n"
    "Jami savollar: <b>{q_total}</b>\n"
    "Javobsiz savollar: <b>{q_unanswered}</b>\n\n"
    "Buyruqlar:\n"
    "/broadcast &lt;xabar&gt;, hammaga xabar yuborish\n"
    "/export, ro'yxatni CSV qilib yuklab olish\n"
    "/cancel, javob yozish rejimini bekor qilish"
)

ADMIN_REPLY_PROMPT = (
    "<b>{name}</b> ga javob yozing.\n"
    "Matn yoki ovozli xabar yuboring. Bekor qilish uchun /cancel."
)
ADMIN_REPLY_SENT = "Javob <b>{name}</b> ga yuborildi."
ADMIN_REPLY_FAILED = (
    "Javob yuborib bo'lmadi. Foydalanuvchi botni to'xtatgan bo'lishi mumkin."
)
ADMIN_REPLY_CANCELLED = "Javob yozish bekor qilindi."
ADMIN_REPLY_UNSUPPORTED = (
    "Faqat matn yoki ovozli xabar yuborishingiz mumkin. Yoki /cancel ni bosing."
)
ADMIN_REPLY_NO_TARGET = (
    "Avval savol ostidagi <b>Javob yozish</b> tugmasini bosing."
)

# Student side: incoming admin reply
STUDENT_REPLY_HEADER = "<b>Administrator javobi:</b>"

# Broadcast
ADMIN_BROADCAST_USAGE = (
    "Foydalanish: <code>/broadcast xabar matni</code>\n"
    "Xabar barcha ro'yxatdan o'tgan foydalanuvchilarga yuboriladi."
)
ADMIN_BROADCAST_STARTED = "Yuborish boshlandi: <b>{total}</b> ta foydalanuvchi."
ADMIN_BROADCAST_DONE = (
    "Tugadi.\n"
    "Muvaffaqiyatli: <b>{ok}</b>\n"
    "Muvaffaqiyatsiz: <b>{fail}</b>"
)
ADMIN_BROADCAST_EMPTY = "Hozircha ro'yxatdan o'tgan foydalanuvchi yo'q."

# Export
ADMIN_EXPORT_EMPTY = "Eksport qilish uchun ma'lumot yo'q."
ADMIN_EXPORT_CAPTION = "Ro'yxat: <b>{total}</b> ta foydalanuvchi."

# ---------------------------------------------------------------------------
# Programs (canonical labels for storage)
# ---------------------------------------------------------------------------

PROGRAM_BAKALAVR = "Bakalavriat"
PROGRAM_MAGISTRATURA = "Magistratura"

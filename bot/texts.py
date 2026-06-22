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
BTN_YES = "Ha, yuborilsin"
BTN_NO = "Yo'q, bekor qilish"
BTN_PREV = "⬅️ Oldingi"
BTN_NEXT = "Keyingi ➡️"
BTN_REFRESH = "🔄 Yangilash"
# Filled with the matched keyword, e.g. "💡 Tayyor javob: stipendiya"
BTN_FAQ_SUGGEST = "💡 Tayyor javob: {keyword}"
BTN_FAQ_CONFIRM_YES = "✅ Ha, yuborilsin"
BTN_FAQ_CONFIRM_NO = "❌ Yo'q"

# Admin reply-keyboard menu (tappable, instead of typing slash commands)
BTN_MENU_QUEUE = "📋 Navbat"
BTN_MENU_STATS = "📊 Statistika"
BTN_MENU_FAQ_LIST = "💬 Tayyor javoblar"
BTN_MENU_FAQ_ADD = "➕ Tayyor javob qo'shish"
BTN_MENU_BROADCAST = "📢 Xabar yuborish"
BTN_MENU_EXPORT = "📥 Eksport"
ADMIN_MENU_HINT = "Quyidagi menyudan foydalaning yoki buyruq yozing."

# Student inline menu
BTN_STU_INFO = "ℹ️ Ma'lumotlarim"
BTN_STU_HELP = "❓ Qanday savol berish"
STUDENT_HELP = (
    "Savol berish uchun shunchaki <b>matn</b> yoki <b>ovozli xabar</b> yuboring.\n"
    "Administrator imkon qadar tezroq javob beradi."
)

# ---------------------------------------------------------------------------
# Registration FSM prompts
# ---------------------------------------------------------------------------

ASK_NAME = (
    "Iltimos, <b>ism va familiyangizni</b> to'liq yozing.\n\n"
    "Masalan: Alisher Karimov"
)
ERR_NAME_INVALID = (
    "Iltimos, to'liq ism va familiyangizni kiriting "
    "(masalan: Alisher Karimov)."
)

ASK_PHONE = (
    "Endi <b>telefon raqamingizni</b> yuboring.\n\n"
    "Quyidagi tugma orqali yuborishingiz yoki qo'lda yozishingiz mumkin.\n"
    "Masalan: +998901234567"
)
ERR_PHONE_INVALID = (
    "Faqat O'zbekiston raqamlari qabul qilinadi (+998...)."
)
ERR_PHONE_TAKEN = (
    "Bu telefon raqam allaqachon ro'yxatdan o'tgan. "
    "Har bir raqam faqat bitta hisob uchun."
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
REG_CANCELLED = "Bekor qilindi."

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
RATE_LIMITED = (
    "Soatiga 10 ta savol yuborish mumkin. Biroz kuting."
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
    "/queue, javobsiz savollar ro'yxati\n"
    "/stats, savollar statistikasi\n"
    "/faq_add, tayyor javob qo'shish\n"
    "/faq_list, tayyor javoblar ro'yxati\n"
    "/faq_del &lt;kalit&gt;, tayyor javobni o'chirish\n"
    "/broadcast &lt;xabar&gt;, hammaga xabar yuborish\n"
    "/export, ro'yxatni CSV qilib yuklab olish\n"
    "/cancel, joriy amalni bekor qilish"
)

# ---------------------------------------------------------------------------
# /queue (admin worklist of unanswered questions)
# ---------------------------------------------------------------------------

ADMIN_QUEUE_EMPTY = "Javobsiz savollar yo'q. ✅"
ADMIN_QUEUE_HEADER = (
    "<b>Javobsiz savollar:</b> {total} ta\n"
    "Sahifa {page}/{pages}\n"
)
# idx = displayed number, matching the "✍️ N" button below the message.
ADMIN_QUEUE_ITEM = (
    "\n<b>{idx}. {name}</b> ({program})\n"
    "{waited}\n"
    "{body}\n"
)
QUEUE_VOICE_LABEL = "[Ovozli]"

# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------

ADMIN_STATS = (
    "<b>Savollar statistikasi</b>\n\n"
    "Jami savollar: <b>{q_total}</b>\n"
    "Javobsiz: <b>{q_unanswered}</b>\n"
    "Javob berilgan: <b>{q_answered}</b>"
)

# ---------------------------------------------------------------------------
# FAQ (canned answers)
# ---------------------------------------------------------------------------

ADMIN_FAQ_ADD_ASK_KEYWORD = (
    "Yangi tayyor javob qo'shamiz.\n\n"
    "Avval qisqa <b>kalit so'z</b> yuboring (masalan: stipendiya).\n"
    "Bekor qilish uchun /cancel."
)
ADMIN_FAQ_ADD_ASK_ANSWER = (
    "Endi <b>{keyword}</b> uchun javob matnini yuboring.\n"
    "Bekor qilish uchun /cancel."
)
ADMIN_FAQ_ADD_KEYWORD_INVALID = (
    "Kalit so'z noto'g'ri. Faqat qisqa matn (harf, raqam, bo'sh joy), "
    "40 belgigacha. Qaytadan yuboring yoki /cancel."
)
ADMIN_FAQ_ADD_ANSWER_INVALID = (
    "Javob matni bo'sh bo'lmasligi kerak. Matn yuboring yoki /cancel."
)
ADMIN_FAQ_ADD_SAVED = (
    "Saqlandi: <b>{keyword}</b>.\n"
    "Javob rejimida <code>/faq {keyword}</code> yozsangiz, bu javob talabaga yuboriladi."
)
ADMIN_FAQ_ADD_OVERWRITE = "(Eslatma: <b>{keyword}</b> avval mavjud edi, yangilandi.)"
ADMIN_FAQ_CANCELLED = "Bekor qilindi."

ADMIN_FAQ_LIST_EMPTY = "Hozircha tayyor javoblar yo'q. Qo'shish uchun /faq_add."
ADMIN_FAQ_LIST_HEADER = "<b>Tayyor javoblar:</b> {total} ta\n"
ADMIN_FAQ_LIST_ITEM = "\n<b>{keyword}</b>\n{answer}\n"

ADMIN_FAQ_DEL_USAGE = "Foydalanish: <code>/faq_del kalit_so'z</code>"
ADMIN_FAQ_DEL_OK = "O'chirildi: <b>{keyword}</b>"
ADMIN_FAQ_DEL_NOT_FOUND = "Bunday kalit so'z topilmadi: <b>{keyword}</b>"

# /faq used inside reply mode
ADMIN_FAQ_REPLY_USAGE = (
    "Foydalanish: <code>/faq kalit_so'z</code>\n"
    "Mavjud kalit so'zlar uchun /faq_list."
)
ADMIN_FAQ_REPLY_NOT_FOUND = (
    "Bunday tayyor javob yo'q: <b>{keyword}</b>. Ro'yxat uchun /faq_list."
)
# /faq tapped/typed outside reply mode
ADMIN_FAQ_NEED_REPLY_MODE = (
    "Tayyor javob yuborish uchun avval savol ostidagi <b>Javob yozish</b> "
    "tugmasini bosing, keyin <code>/faq kalit_so'z</code> yuboring.\n"
    "Yangi savol bildirishnomasidagi <b>Tayyor javob</b> tugmasi esa bir bosishda yuboradi."
)
# Suggestion hint appended to a fresh question notification. Plain text (no
# <code>) so the /faq command stays visible; the one-tap button does the work.
ADMIN_FAQ_SUGGESTION = "\n\n💡 Tavsiya: /faq {keyword}"
# Suggestion outcomes (callback answers / confirmation flow)
ADMIN_FAQ_SUGGEST_SENT = "Tayyor javob yuborildi: {keyword}"
ADMIN_FAQ_SUGGEST_GONE = "Tavsiya endi mavjud emas. Qo'lda javob bering."
ADMIN_FAQ_SUGGEST_ALREADY = "Bu savolga allaqachon javob berilgan."
# Shown (as a new message) when the admin taps the suggestion, before sending.
# {answer} is the full canned answer so the admin reviews it before confirming.
ADMIN_FAQ_CONFIRM = (
    "Quyidagi tayyor javob (<b>{keyword}</b>) talabaga yuborilsinmi?\n\n"
    "{answer}"
)
ADMIN_FAQ_CONFIRM_SENT = "✅ Yuborildi: <b>{keyword}</b>"
ADMIN_FAQ_CONFIRM_CANCELLED = "Bekor qilindi. Tayyor javob yuborilmadi."

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

# Appended to a notification after another admin has replied, so admins who
# did not handle the question can see at a glance that it is closed.
NOTIFICATION_ANSWERED_SUFFIX = "\n\n✅ Javob berildi"

# Broadcast
ADMIN_BROADCAST_USAGE = (
    "Foydalanish: <code>/broadcast xabar matni</code>\n"
    "Xabar barcha ro'yxatdan o'tgan foydalanuvchilarga yuboriladi."
)
ADMIN_BROADCAST_PREVIEW = (
    "Bu xabar <b>{total}</b> ta talabaga yuboriladi. Tasdiqlaysizmi?\n\n"
    "<i>Ko'rinishi:</i>\n{preview}"
)
ADMIN_BROADCAST_CANCELLED = "Yuborish bekor qilindi."
ADMIN_BROADCAST_STARTED = "Yuborish boshlandi: <b>{total}</b> ta foydalanuvchi."
ADMIN_BROADCAST_DONE = (
    "Tugadi.\n"
    "Muvaffaqiyatli: <b>{ok}</b>\n"
    "Muvaffaqiyatsiz: <b>{fail}</b>"
)
ADMIN_BROADCAST_EMPTY = "Hozircha ro'yxatdan o'tgan foydalanuvchi yo'q."
ADMIN_BROADCAST_STALE = (
    "Bu so'rov eskirgan. Yangi xabar uchun /broadcast ni qaytadan yuboring."
)

# Export
ADMIN_EXPORT_EMPTY = "Eksport qilish uchun ma'lumot yo'q."
ADMIN_EXPORT_CAPTION = "Ro'yxat: <b>{total}</b> ta foydalanuvchi."

# Daily auto-backup (sent to every admin)
ADMIN_BACKUP_CAPTION = (
    "Kunlik zaxira nusxa ({date})\n"
    "Jami talabalar: {total}\n"
    "Javobsiz savollar: {q_unanswered}"
)

# ---------------------------------------------------------------------------
# Programs (canonical labels for storage)
# ---------------------------------------------------------------------------

PROGRAM_BAKALAVR = "Bakalavriat"
PROGRAM_MAGISTRATURA = "Magistratura"

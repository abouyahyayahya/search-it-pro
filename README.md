# Search It (Fixed)
نسخة مُحسَّنة من تطبيق Streamlit الذي يبحث في **OpenAlex**.

## التشغيل
```bash
pip install -r requirements.txt
streamlit run app.py
```

> **مهم**: للحصول على حصص أكثر ثباتًا من OpenAlex، يُستحسن تعيين متغير البيئة `OPENALEX_MAILTO` إلى بريدك:
```bash
export OPENALEX_MAILTO="you@example.com"
```

## ما الذي تم إصلاحه؟
- إزالة الاعتماد على ملف خارجي مفقود `searchh_complete_plus.py` واستبداله بدوال مدمجة.
- تحمّل أفضل للأخطاء ورسائل واضحة عند فشل الطلبات.
- تصدير Excel بمحرك احتياطي تلقائي (xlsxwriter أو openpyxl).
- دعم `st.rerun` إن توفر لتوافق الإصدارات الحديثة من Streamlit.
- فلترة "استثناء الكلمات" تعمل على **العنوان والملخّص** بدل العنوان فقط.
- واجهة إجراءات بسيطة (PDF | المصدر | الاستشهادات) لكل نتيجة.

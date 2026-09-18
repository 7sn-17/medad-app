import os
import sys
import json
import xml.etree.ElementTree as ET
import google.generativeai as genai
import arabic_reshaper
from bidi.algorithm import get_display

class MedadEngine:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self.model = None

    def validate_api_key(self) -> bool:
        """فحص مفتاح Gemini API والتأكد من فعاليته قبل بدء أي عملية"""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            response = self.model.generate_content("Ping")
            if response and response.text:
                print("SUCCESS: مفتاح Gemini API يعمل بنجاح.")
                return True
        except Exception as e:
            print(f"ERROR: مفتاح Gemini API غير صالح أو معطل: {e}")
            return False
        return False

    def reshape_arabic(self, text: str) -> str:
        """تشكيل الحروف العربية وتصحيح الاتجاه (RTL Fix) للألعاب"""
        if not text or not isinstance(text, str):
            return text
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception:
            return text

    def translate_batch(self, text_list: list) -> dict:
        """ترجمة نصوص اللعبة عبر Gemini مع حماية المتغيرات البرمجية والرموز"""
        prompt = f"""
        أنت مترجم محترف ألعاب أندرويد. قم بترجمة النصوص التالية إلى اللغة العربية.
        قواعد حارمة:
        1. احتفظ بنفس الرموز والمتغيرات مثل (%s, %d, %1$s, {{0}}, \\n) كما هي بدون أي تغيير.
        2. لا تترجم الكلمات البرمجية أو المعرفات.
        3. أرجع النتيجة حصراً بصيغة JSON: {{"النص الأصلي": "الترجمة العربية"}}

        النصوص المراد ترجمتها:
        {json.dumps(text_list, ensure_ascii=False)}
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"WARNING: حدث خطأ أثناء ترجمة هذه الدفعة: {e}")
            return {}

    def process_strings_file(self, input_path: str, output_path: str):
        if not os.path.exists(input_path):
            print(f"ERROR: لم يتم العثور على ملف النصوص: {input_path}")
            sys.exit(1)

        print("INFO: تفكيك وقراءة ملف النصوص...")
        tree = ET.parse(input_path)
        root = tree.getroot()

        original_texts = []
        elements_map = []

        for elem in root.findall('string'):
            if elem.text and not elem.text.startswith("http") and len(elem.text.strip()) > 0:
                original_texts.append(elem.text)
                elements_map.append(elem)

        if not original_texts:
            print("INFO: لا توجد نصوص بداخل الملف تحتاج للترجمة.")
            return

        print(f"INFO: معالجة وترجمة {len(original_texts)} نص على دفعات...")
        batch_size = 30
        translations = {}
        for i in range(0, len(original_texts), batch_size):
            batch = original_texts[i:i + batch_size]
            result = self.translate_batch(batch)
            translations.update(result)

        for elem in elements_map:
            orig = elem.text
            if orig in translations:
                elem.text = self.reshape_arabic(translations[orig])

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        print(f"SUCCESS: تم تعريب الملف بنجاح وتشكيل الخط العربي في: {output_path}")

if __name__ == "__main__":
    api_key_input = os.getenv("GEMINI_API_KEY", "")
    input_file = os.getenv("TARGET_FILE", "input/strings.xml")
    output_file = os.getenv("OUTPUT_FILE", "output/strings.xml")

    engine = MedadEngine(api_key=api_key_input)

    if not engine.validate_api_key():
        sys.exit(1)

    engine.process_strings_file(input_file, output_file)

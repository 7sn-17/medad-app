import os
import sys
import json
import zipfile
import re
import urllib.request
import urllib.error

# محرك تعريب ألعاب الأندرويد التلقائي (مِدَاد Engine v2.0)

def translate_text_with_gemini(text, api_key):
    """إرسال النصوص إلى Gemini API مع حماية وتوجيهات تعريب دقيقة"""
    if not text.strip():
        return text
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = (
        "You are an expert game translator. Translate the following text into natural, fluent Arabic. "
        "Keep placeholders, code symbols, variables (like %s, {0}, \\n), and brackets intact. "
        "Return ONLY the direct translated string without quotes or extra text:\n\n" + text
    )
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print(f"[Warning] Translation failed for text: {text}. Error: {e}")
        return text

def process_xml_strings(file_path, api_key):
    """استخراج وترجمة النصوص داخل ملفات XML الخاص بـ Android Resources"""
    print(f"[*] Processing XML file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # البحث عن عناصر <string name="...">Text</string>
    pattern = re.compile(r'<string name="([^"]+)">([^<]+)</string>')
    
    def replacer(match):
        name = match.group(1)
        original_text = match.group(2)
        translated = translate_text_with_gemini(original_text, api_key)
        return f'<string name="{name}">{translated}</string>'

    new_content = pattern.sub(replacer, content)
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"[✓] Successfully translated: {file_path}")

if __name__ == "__main__":
    print("=== Medad Translation Engine Started ===")
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    if not api_key:
        print("[!] Error: GEMINI_API_KEY is missing!")
        sys.exit(1)
        
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".xml") and "strings" in file:
                full_path = os.path.join(root, file)
                process_xml_strings(full_path, api_key)
                
    print("=== Translation Complete ===")

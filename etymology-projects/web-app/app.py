from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import os
from datetime import datetime
from gtts import gTTS
import hashlib
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///etymology.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 음성 파일을 저장할 디렉토리 설정
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'audio')
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

db = SQLAlchemy(app)

class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)
    phonetic = db.Column(db.String(100))
    audio_url = db.Column(db.String(500))
    raw_data = db.Column(db.Text)  # API 응답 전체를 JSON으로 저장

class Vocabulary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word_id = db.Column(db.Integer, db.ForeignKey('word.id'), nullable=False)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text)
    word = db.relationship('Word', backref=db.backref('vocabulary', lazy=True))

@app.template_filter('parse_json')
def parse_json(value):
    return json.loads(value) if value else []

def translate_text(text):
    """Google Translate API를 사용하여 텍스트를 번역합니다."""
    if not text:
        return None
    
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "ko",
            "dt": "t",
            "q": text
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            result = response.json()
            translated = ''
            for sentence in result[0]:
                if sentence[0]:
                    translated += sentence[0]
            return translated
        return None
    except Exception as e:
        print(f"번역 중 오류 발생: {e}")
        return None

def generate_audio(word):
    """단어의 발음을 생성하고 저장합니다."""
    try:
        filename = hashlib.md5(word.encode()).hexdigest() + '.mp3'
        filepath = os.path.join(AUDIO_DIR, filename)
        
        if not os.path.exists(filepath):
            tts = gTTS(text=word, lang='en', slow=False)
            tts.save(filepath)
        
        return f'/static/audio/{filename}'
    except Exception as e:
        print(f"음성 생성 중 오류 발생: {e}")
        return None

def fetch_word_info(word):
    """Free Dictionary API에서 단어 정보를 가져옵니다."""
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                word_data = data[0]
                
                # 발음 오디오 URL (API 제공 또는 TTS 생성)
                audio_url = None
                if 'phonetics' in word_data and word_data['phonetics']:
                    for phonetic in word_data['phonetics']:
                        if phonetic.get('audio'):
                            audio_url = phonetic['audio']
                            break
                
                if not audio_url:
                    audio_url = generate_audio(word)
                
                return {
                    'word': word_data.get('word', word),
                    'phonetic': word_data.get('phonetic', None),
                    'audio_url': audio_url,
                    'raw_data': json.dumps(word_data)  # API 응답 전체를 저장
                }
    except Exception as e:
        print(f"API 호출 중 오류 발생: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate():
    """텍스트를 번역합니다."""
    data = request.get_json()
    if 'text' in data:
        translated = translate_text(data['text'])
        if translated:
            return jsonify({'translated': translated})
    return jsonify({'error': '번역에 실패했습니다.'}), 400

@app.route('/search')
def search():
    query = request.args.get('q', '')
    words = Word.query.filter(Word.word.like(f'%{query}%')).all()
    
    if not words and query.strip():
        word_info = fetch_word_info(query.lower())
        if word_info:
            new_word = Word(
                word=word_info['word'],
                phonetic=word_info['phonetic'],
                audio_url=word_info['audio_url'],
                raw_data=word_info['raw_data']
            )
            try:
                db.session.add(new_word)
                db.session.commit()
                words = [new_word]
            except Exception as e:
                print(f"데이터베이스 저장 중 오류 발생: {e}")
                db.session.rollback()
    
    return render_template('search.html', words=words, query=query)

@app.route('/vocabulary/add/<int:word_id>', methods=['POST'])
def add_to_vocabulary(word_id):
    """단어장에 단어를 추가합니다."""
    note = request.form.get('note', '')
    
    existing = Vocabulary.query.filter_by(word_id=word_id).first()
    if existing:
        return jsonify({'message': '이미 단어장에 있는 단어입니다.'})
    
    vocab = Vocabulary(word_id=word_id, note=note)
    db.session.add(vocab)
    db.session.commit()
    
    return jsonify({'message': '단어장에 추가되었습니다.'})

@app.route('/vocabulary')
def view_vocabulary():
    """단어장을 보여줍니다."""
    vocab_items = Vocabulary.query.order_by(Vocabulary.added_date.desc()).all()
    return render_template('vocabulary.html', vocab_items=vocab_items)

@app.route('/vocabulary/remove/<int:vocab_id>', methods=['POST'])
def remove_from_vocabulary(vocab_id):
    """단어장에서 단어를 제거합니다."""
    vocab = Vocabulary.query.get_or_404(vocab_id)
    db.session.delete(vocab)
    db.session.commit()
    return jsonify({'message': '단어장에서 제거되었습니다.'})

@app.route('/vocabulary/edit/<int:vocab_id>', methods=['POST'])
def edit_vocabulary_note(vocab_id):
    """단어장의 노트를 수정합니다."""
    vocab = Vocabulary.query.get_or_404(vocab_id)
    data = request.get_json()
    
    if 'note' in data:
        vocab.note = data['note']
        db.session.commit()
        return jsonify({'message': '노트가 수정되었습니다.'})
    
    return jsonify({'message': '노트 수정에 실패했습니다.'}), 400

def init_db():
    """데이터베이스를 초기화합니다."""
    with app.app_context():
        db.drop_all()
        db.create_all()

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 
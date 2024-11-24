from flask import Flask, render_template, request, jsonify, redirect
import requests
from flask_sqlalchemy import SQLAlchemy
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from datetime import datetime


app = Flask(__name__)

# MySQL 데이터베이스 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1234@localhost/music_requests'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Spotify API Client ID와 Client Secret 설정
SPOTIPY_CLIENT_ID = 'your client id'
SPOTIPY_CLIENT_SECRET = 'your client token'

# Spotify 인증 설정 (Client Credentials Flow)
client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# 데이터베이스 테이블 모델 정의
class SongRequest(db.Model):
    __tablename__ = 'song_request'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False, default="Unknown")
    track_id = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())



# 초기화: 데이터베이스 테이블 생성
with app.app_context():
    db.create_all()

# 홈 페이지 라우트
@app.route('/')
def home():
    return render_template('index.html')

# Spotify 검색 엔드포인트
@app.route('/search', methods=['GET'])
def search_song():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    # Spotify API로 검색 요청
    results = sp.search(q=query, type='track', limit=5)
    print("Spotify API Response:", results)  # 응답을 출력해서 구조 확인

    tracks = results['tracks']['items']
    songs = [
        {
            "title": track['name'],
            "artist": track['artists'][0]['name'] if track['artists'] else "Unknown",  # artist 처리
            "track_id": track['id'],
            "album": track['album']['name'],
            "thumbnail": track['album']['images'][0]['url'] if track['album']['images'] else None
        }
        for track in tracks
    ]
    return jsonify(songs)




# 노래 신청 저장 엔드포인트
@app.route('/request', methods=['POST'])
def save_request():
    data = request.json
    title = data.get('title')
    track_id = data.get('track_id')
    artist = data.get('artist')
    ip_address = request.remote_addr
    
    if not title or not track_id or not artist:
        return jsonify({"error": "Invalid request data"}), 400

    # localhost나 127.0.0.1이 아닌 경우에만 IP 제한 체크
    if ip_address not in ['127.0.0.1', 'localhost']:
        # 오늘 날짜의 시작 시간 구하기
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 같은 IP에서 오늘 이미 신청한 곡이 있는지 확인
        existing_request = SongRequest.query.filter(
            SongRequest.ip_address == ip_address,
            SongRequest.created_at >= today
        ).first()
        
        if existing_request:
            return jsonify({
                "error": "limit_exceeded",
                "message": "오늘은 이미 곡을 신청하셨습니다. 내일 다시 시도해주세요."
            }), 429  # Too Many Requests
    
    # 중복 곡 체크
    existing_song = SongRequest.query.filter_by(track_id=track_id).first()
    if existing_song:
        return jsonify({
            "error": "duplicate",
            "message": f"'{title}' - {artist} 곡은 이미 신청되어 있습니다."
        }), 409

    # 새로운 요청 저장
    new_request = SongRequest(
        title=title,
        track_id=track_id,
        artist=artist,
        ip_address=ip_address
    )
    db.session.add(new_request)
    db.session.commit()

    return jsonify({"message": f"Song '{title}' by {artist} saved successfully."})


# 요청 내역 조회 엔드포인트
@app.route('/requests', methods=['GET'])
def get_requests():
    all_requests = SongRequest.query.all()
    return jsonify([{
        "id": req.id,
        "title": req.title,
        "artist": req.artist,  # 가수 정보 포함
        "track_id": req.track_id,
        "created_at": req.created_at
    } for req in all_requests])


@app.route('/clear_requests', methods=['DELETE'])
def clear_requests():
    # 모든 노래 요청 삭제
    try:
        SongRequest.query.delete()  # 모든 항목 삭제
        db.session.commit()  # 변경사항 커밋
        return jsonify({"message": "All song requests have been deleted."}), 200
    except Exception as e:
        db.session.rollback()  # 에러 발생 시 롤백
        return jsonify({"error": str(e)}), 500
    
@app.route('/requests/<int:request_id>', methods=['DELETE'])
def delete_request(request_id):
    try:
        # 해당 ID의 요청 찾기
        song_request = SongRequest.query.get_or_404(request_id)
        
        # 데이터베이스에서 삭제
        db.session.delete(song_request)
        db.session.commit()
        
        return jsonify({"message": f"Song request {request_id} deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()  # 오류 발생 시 롤백
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(
        debug=True, 
        host='0.0.0.0',
        port=5000,
    )

import sys
import requests
import random
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QLabel, QCheckBox, QWidget, QMessageBox, 
                           QScrollArea, QInputDialog, QProgressDialog, QFrame,
                           QStyle, QSizePolicy, QLineEdit)
from PyQt5.QtGui import QFont, QPalette, QColor, QIntValidator
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import webbrowser

# 서버 URL 설정
SERVER_URL = "http://127.0.0.1:5000"

# Spotify API 설정
SPOTIPY_CLIENT_ID = 'your spotify client id'
SPOTIPY_CLIENT_SECRET = 'your spotify client secret'
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:9090'

# Spotify 인증 설정
auth_manager = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope="playlist-modify-public",
    open_browser=True
)
sp = Spotify(auth_manager=auth_manager)

class SongItem:
    def __init__(self, id, title, artist, track_id):
        self.id = id
        self.title = title
        self.artist = artist
        self.track_id = track_id

class PlaylistCreationThread(QThread):
    result_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, selected_songs, sp, playlist_name):
        super().__init__()
        self.selected_songs = selected_songs
        self.sp = sp
        self.playlist_name = playlist_name

    def run(self):
        if not self.selected_songs:
            self.result_signal.emit("No songs selected!")
            return
        
        try:
            self.progress_signal.emit(20)
            # 현재 사용자 ID 가져오기
            user_id = self.sp.me()['id']
            
            self.progress_signal.emit(40)
            # 플레이리스트 생성
            playlist = self.sp.user_playlist_create(
                user=user_id,
                name=self.playlist_name,
                public=True,
                description="Generated from Music Request Viewer"
            )
            
            self.progress_signal.emit(60)
            # track_id 리스트 생성
            track_ids = [song.track_id for song in self.selected_songs]
            
            self.progress_signal.emit(80)
            # 플레이리스트에 곡 추가
            if track_ids:
                self.sp.playlist_add_items(playlist['id'], track_ids)
                playlist_url = playlist['external_urls']['spotify']
                self.result_signal.emit(f"플레이리스트가 생성되었습니다!\n총 {len(track_ids)}곡이 추가되었습니다.\n플레이리스트 URL: {playlist_url}")
                webbrowser.open(playlist_url)
            else:
                self.result_signal.emit("플레이리스트에 추가할 곡이 없습니다!")
            
            self.progress_signal.emit(100)
                
        except Exception as e:
            self.result_signal.emit(f"플레이리스트 생성 중 오류 발생: {str(e)}")

class SongItemWidget(QFrame):
    def __init__(self, song, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(1)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        layout.addWidget(self.checkbox)
        
        song_info = QLabel(f"{song.title} - {song.artist}")
        song_info.setFont(QFont("Arial", 10))
        song_info.setStyleSheet("color: white;")
        layout.addWidget(song_info)
        
        layout.addStretch()
        
        # 삭제 버튼
        delete_button = QPushButton("삭제")
        delete_button.setFixedSize(50, 25)
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)
        delete_button.clicked.connect(lambda: self.delete_song(song))
        layout.addWidget(delete_button)
        
        # 스타일시트
        self.setStyleSheet("""
            SongItemWidget {
                background-color: #2d2d2d;
                border-radius: 8px;
                margin: 2px;
                padding: 5px;
            }
            SongItemWidget:hover {
                background-color: #1DB954;
            }
            QLabel {
                color: white;
                font-family: 'Segoe UI', 'SF Pro Display';
                font-size: 13px;
                font-weight: 500;
            }
            SongItemWidget:hover QLabel {
                color: black;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #1DB954;
                border-radius: 4px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #1DB954;
            }
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                font-family: 'Segoe UI', 'SF Pro Display';
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        # Qt 메서드드
        self.setCursor(Qt.PointingHandCursor)
        
    def mousePressEvent(self, event):
        """위젯 클릭 시 체크박스 토글"""
        if event.button() == Qt.LeftButton:
            self.checkbox.setChecked(not self.checkbox.isChecked())
            super().mousePressEvent(event)
            
    def delete_song(self, song):
        reply = QMessageBox.question(
            self, 
            '곡 삭제', 
            f'"{song.title}"을(를) 정말 삭제하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                #서버 삭제 요청
                response = requests.delete(f"{SERVER_URL}/requests/{song.id}")
                
                if response.status_code == 200:
                    #song_checkboxes 딕셔너리 체크박스 제거
                    main_window = self.window()
                    if hasattr(main_window, 'song_checkboxes') and song.id in main_window.song_checkboxes:
                        del main_window.song_checkboxes[song.id]
                    
                    #위젯 제거
                    self.parent().layout().removeWidget(self)
                    self.deleteLater()
                    
                    QMessageBox.information(self, "성공", "곡이 성공적으로 삭제되었습니다.")
                    
                    #메인 윈도우 새로고침 메서드 호출
                    main_window.load_song_requests()
                else:
                    QMessageBox.critical(self, "오류", "서버에서 곡을 삭제하는데 실패했습니다.")
                    
            except Exception as e:
                QMessageBox.critical(self, "오류", f"삭제 중 오류가 발생했습니다: {str(e)}")

class MusicRequestApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Request Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.selected_songs = []
        self.song_checkboxes = {}
        
        
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Text, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        app = QApplication.instance()
        app.setPalette(dark_palette)
        
        #스타일시트트
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 5px;
                background-color: #1DB954;
                color: white;
                font-family: 'Segoe UI', 'SF Pro Display';
                font-weight: 600;
                font-size: 13px;
                border: none;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
            QPushButton:pressed {
                background-color: #1aa34a;
            }
            QLabel {
                color: white;
                font-family: 'Segoe UI', 'SF Pro Display';
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #333333;
                border-radius: 5px;
                background-color: #2d2d2d;
                color: white;
                font-family: 'Segoe UI', 'SF Pro Display';
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #1DB954;
            }
            QScrollArea {
                background-color: #2d2d2d;
                border: 2px solid #333333;
                border-radius: 8px;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #2d2d2d;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #4d4d4d;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5d5d5d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QCheckBox {
                color: white;
            }
        """)
        
        # 메인 위젯 설정
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        # 레이아웃 설정
        self.layout = QVBoxLayout(self.main_widget)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(30, 30, 30, 30)
        
        # 상단 정보 영역
        self.header_layout = QHBoxLayout()
        
        # 상태 레이블
        self.status_label = QLabel("노래 목록을 불러오는 중...")
        self.status_label.setFont(QFont("Segoe UI", 12, QFont.Medium))
        self.header_layout.addWidget(self.status_label)
        
        # 선택된 곡 수 표시 레이블
        self.selection_label = QLabel("선택된 곡: 0")
        self.selection_label.setFont(QFont("Segoe UI", 12, QFont.Medium))
        self.selection_label.setAlignment(Qt.AlignRight)
        self.header_layout.addWidget(self.selection_label)
        
        self.layout.addLayout(self.header_layout)
        
        # 버튼 컨테이너 생성
        button_container = QHBoxLayout()

        # 왼쪽: 전체 선택 버튼
        self.select_all_button = QPushButton("전체 선택")
        self.select_all_button.clicked.connect(self.toggle_all_selection)
        self.select_all_button.setFixedWidth(150)
        button_container.addWidget(self.select_all_button)

        # 중앙: 랜덤 선택 입력 필드와 버튼
        self.random_count_input = QLineEdit()
        self.random_count_input.setPlaceholderText("선택할 곡 수")
        self.random_count_input.setFixedWidth(100)
        self.random_count_input.setValidator(QIntValidator(1, 9999))
        self.random_count_input.setAlignment(Qt.AlignCenter)
        button_container.addWidget(self.random_count_input)

        self.random_select_button = QPushButton("랜덤 선택")
        self.random_select_button.clicked.connect(self.select_random_songs)
        self.random_select_button.setFixedWidth(150)
        button_container.addWidget(self.random_select_button)

        # 오른쪽 여백
        button_container.addStretch()

        # 메인 레이아웃에 버튼 컨테이너 추가
        self.layout.addLayout(button_container)
        
        # 스크롤 영역 설정
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        
        self.song_list_widget = QWidget()
        self.song_list_layout = QVBoxLayout(self.song_list_widget)
        self.song_list_layout.setSpacing(8)
        self.song_list_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_area.setWidget(self.song_list_widget)
        self.layout.addWidget(self.scroll_area)
        
        # 튼 레이아웃
        self.button_layout = QHBoxLayout()
        
        # 새로고침 버튼
        self.refresh_button = QPushButton("새로고침")
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.refresh_button.clicked.connect(self.load_song_requests)
        self.button_layout.addWidget(self.refresh_button)
        
        # 플레이리스트 생성 버튼
        self.create_playlist_button = QPushButton("플레이리스트 생성")
        self.create_playlist_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.create_playlist_button.clicked.connect(self.create_playlist)
        self.button_layout.addWidget(self.create_playlist_button)
        
        self.layout.addLayout(self.button_layout)
        
        # 프로그레스 다이얼로그 초기화
        self.progress_dialog = None
        
        # 초기 데이터 로드
        self.load_song_requests()
    
    def load_song_requests(self):
        """서버서 노래 요청 목록을 불러옴"""
        self.status_label.setText("노래 목록을 불러오는 중...")
        try:
            response = requests.get(f"{SERVER_URL}/requests")
            if response.status_code == 200:
                requests_data = response.json()
                self.display_song_requests(requests_data)
                self.status_label.setText(f"총 {len(requests_data)}개의 노래가 로드되었습니다.")
            else:
                self.status_label.setText("서버에서 노래 목록을 가져오는데 실패했습니다.")
                QMessageBox.critical(self, "Error", "서버에서 노래 목록을 가져오는데 실패했습니다.")
        except Exception as e:
            self.status_label.setText(f"오류 발생: {str(e)}")
            QMessageBox.critical(self, "Error", f"오류 발생: {str(e)}")
    
    def display_song_requests(self, requests_data):
        """노래 요청 목록을 화면에 표시"""
        # 기존 노래 ID 목록 저장
        existing_song_ids = set(self.song_checkboxes.keys())
        new_song_ids = set(request['id'] for request in requests_data)
        
        # 삭제된 노래 제거
        removed_songs = existing_song_ids - new_song_ids
        for song_id in removed_songs:
            if song_id in self.song_checkboxes:
                widget = self.song_checkboxes[song_id].parent()
                widget.deleteLater()
                del self.song_checkboxes[song_id]
        
        # 새로운 노래만 추가
        for request in requests_data:
            if request['id'] not in existing_song_ids:
                song = SongItem(
                    id=request['id'],
                    title=request['title'],
                    artist=request['artist'],
                    track_id=request['track_id']
                )
                
                # 노래 항목 위젯 생성
                item_widget = SongItemWidget(song)
                self.song_list_layout.addWidget(item_widget)
                
                # 체크박스 연결
                item_widget.checkbox.stateChanged.connect(
                    lambda state, s=song: self.toggle_selection(state, s))
                self.song_checkboxes[song.id] = item_widget.checkbox
        
        # 마지막에 스트레치 추가 (기존 스트레치 제거 후 새로 추가)
        for i in reversed(range(self.song_list_layout.count())):
            item = self.song_list_layout.itemAt(i)
            if item.widget() is None:  # 스트레치 아이템인 경우
                self.song_list_layout.removeItem(item)
        self.song_list_layout.addStretch()
        
        self.update_selection_label()
    
    def toggle_selection(self, state, song):
        """체크박스 태 변경 처리"""
        if state == 2:  # Checked
            if song not in self.selected_songs:
                self.selected_songs.append(song)
        else:  # Unchecked
            if song in self.selected_songs:
                self.selected_songs.remove(song)
        
        self.update_selection_label()
    
    def update_selection_label(self):
        """선택된 곡 수 업데이트"""
        self.selection_label.setText(f"선택된 곡: {len(self.selected_songs)}")
    
    def toggle_all_selection(self):
        """전체 선택/해제 토글"""
        # 재 모든 곡이 선택되어 있는지 확인
        all_selected = all(checkbox.isChecked() for checkbox in self.song_checkboxes.values())
        
        # 전체 선택/해제 상태 변경
        for checkbox in self.song_checkboxes.values():
            checkbox.setChecked(not all_selected)
        
        # 버튼 텍스트 업데이트
        self.select_all_button.setText("전체 해제" if not all_selected else "전체 선택")
    
    def create_playlist(self):
        """선택된 노래로 플레이리스트 생성"""
        if not self.selected_songs:
            QMessageBox.warning(self, "Warning", "선택된 노래가 없습니다!")
            return
        
        # 플레이리스트 이름 입력 받기
        playlist_name, ok = QInputDialog.getText(
            self, 
            "플레이리스트 이름",
            "생성할 플레이리스트의 이름을 입력하세요:",
            text=f"My Playlist {random.randint(1, 1000)}"
        )
        
        if not ok or not playlist_name.strip():
            return
        
        # 프로그레스 다이얼로그 생성
        self.progress_dialog = QProgressDialog(
            "플레이리스트 생성 중...", 
            None, 0, 100, self
        )
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.show()
        
        # 플레이리스트 생성 스레드 시작
        self.playlist_thread = PlaylistCreationThread(
            self.selected_songs, 
            sp,
            playlist_name
        )
        self.playlist_thread.result_signal.connect(self.show_playlist_result)
        self.playlist_thread.progress_signal.connect(self.update_progress)
        self.playlist_thread.start()
    
    def update_progress(self, value):
        """프로그레스 다이얼로그 업데이트"""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
    
    def show_playlist_result(self, message):
        """플레이리스트 생성 결과 표시"""
        QMessageBox.information(self, "Playlist Creation Result", message)
    
    def select_random_songs(self):
        """입력된 개수만큼 랜덤으로 노래 선택 (기존 선택 유지)"""
        try:
            count = int(self.random_count_input.text())
            if count <= 0:
                QMessageBox.warning(self, "Warning", "1 이상의 숫자를 입력하세요!")
                return
            
            # 현재 체크된 체크박스들과 체크되지 않은 체크박스들을 분리
            checked_boxes = []
            unchecked_boxes = []
            for checkbox in self.song_checkboxes.values():
                if checkbox.isChecked():
                    checked_boxes.append(checkbox)
                else:
                    unchecked_boxes.append(checkbox)
            
            # 추가로 선택해야 할 개수 계산
            additional_needed = count - len(checked_boxes)
            
            if additional_needed <= 0:
                # 이미 충분한 곡이 선택되어 있음
                QMessageBox.warning(self, "Warning", f"이미 {len(checked_boxes)}곡이 선택되어 있습니다!")
                return
            
            if additional_needed > len(unchecked_boxes):
                QMessageBox.warning(self, "Warning", 
                    f"추가로 선택 가능한 곡이 {len(unchecked_boxes)}개 뿐입니다!")
                additional_needed = len(unchecked_boxes)
            
            # 추가 랜덤 선택
            if additional_needed > 0:
                additional_selections = random.sample(unchecked_boxes, additional_needed)
                for checkbox in additional_selections:
                    checkbox.setChecked(True)
            
        except ValueError:
            QMessageBox.warning(self, "Warning", "올바른 숫자를 입력하세요!")
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 시스템별 기본 폰트 설정
    if sys.platform == "darwin":  # macOS
        app.setFont(QFont('SF Pro Display', 10))
    else:  # Windows
        app.setFont(QFont('Segoe UI', 10))
    
    window = MusicRequestApp()
    window.show()
    sys.exit(app.exec_())

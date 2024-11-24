// 검색 함수 분리
function searchSongs() {
    const query = document.getElementById('searchInput').value;
    if (!query.trim()) return; // 빈 검색어 방지

    fetch(`/search?query=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            displaySongs(data);
        })
        .catch(error => {
            console.error("Error fetching songs:", error);
        });
}

// 검색 버튼 클릭 이벤트
document.getElementById('searchBtn').addEventListener('click', searchSongs);

// 검색창 엔터 키 이벤트
document.getElementById('searchInput').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault(); // 폼 제출 방지
        searchSongs();
    }
});

// 노래 검색 결과를 HTML에 표시하는 함수
function displaySongs(songs) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';  // 이전 검색 결과 초기화

    songs.forEach(song => {
        const songDiv = document.createElement('div');
        songDiv.classList.add('song');

        const thumbnail = song.thumbnail ? `<img src="${song.thumbnail}" alt="Album Cover">` : '';
        songDiv.innerHTML = `
            <h3>${song.title}</h3>
            <p>Artist: ${song.artist}</p>
            <p>Album: ${song.album}</p>
            ${thumbnail}
            <button class="request-btn" data-track-id="${song.track_id}" data-title="${song.title}" data-artist="${song.artist}">Request</button>
        `;

        // 신청 버튼 클릭 이벤트
        songDiv.querySelector('.request-btn').addEventListener('click', function() {
            const trackId = song.track_id;
            const title = song.title;
            const artist = song.artist;  // artist 정보를 추가

            // 서버로 신청 데이터를 보내는 요청
            fetch('/request', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: title, track_id: trackId, artist: artist })  // artist 포함
            })
            .then(response => response.json())
            .then(data => alert(data.message))
            .catch(error => console.error("Error requesting song:", error));
        });

        resultsDiv.appendChild(songDiv);
    });
}

import { useEffect, useState } from "react";
import { api } from "./api";
import "./StudyRoomView.css";

export default function StudyRoomView() {
  const [rooms, setRooms] = useState([]);
  const [title, setTitle] = useState("고1 수학 하브루타");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = () => api("/rooms").then((result) => setRooms(result.rooms)).catch((requestError) => setError(requestError.message));
  useEffect(() => { load(); }, []);

  const createRoom = async (event) => {
    event.preventDefault(); setError(""); setNotice("");
    try {
      const result = await api("/rooms", { method: "POST", body: JSON.stringify({ title, subject: "수학", grade: "고등학교 1학년", max_members: 4 }) });
      setNotice(`학습방을 만들었습니다. 초대 코드: ${result.room.invite_code}`); load();
    } catch (requestError) { setError(requestError.message); }
  };
  const joinRoom = async (event) => {
    event.preventDefault(); setError(""); setNotice("");
    try {
      const result = await api("/rooms/join", { method: "POST", body: JSON.stringify({ invite_code: inviteCode.toUpperCase() }) });
      setNotice(result.message); setInviteCode(""); load();
    } catch (requestError) { setError(requestError.message); }
  };

  return (
    <main className="study-room-page">
      <div className="room-panel">
        <header><h2>스터디룸</h2><p>친구와 학습방을 공유하거나 AI 튜터 세션을 시작할 공간을 관리하세요.</p></header>
        <div className="room-actions">
          <form onSubmit={createRoom}><h3>새 학습방</h3><input value={title} onChange={(e) => setTitle(e.target.value)} required /><button className="btn-primary">생성하기</button></form>
          <form onSubmit={joinRoom}><h3>초대 코드 참여</h3><input value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} maxLength={6} placeholder="6자리 코드" required /><button className="btn-primary">참여하기</button></form>
        </div>
        {notice && <div className="room-notice">{notice}</div>}{error && <div className="room-error">{error}</div>}
        <section className="room-list"><h3>내 학습방 {rooms.length}개</h3>{rooms.map((room) => (
          <article key={room.id} className="room-item"><div><strong>{room.title}</strong><p>{room.subject} · {room.grade} · {room.member_count}/{room.max_members}명</p></div><button onClick={() => navigator.clipboard.writeText(room.invite_code)}>{room.invite_code} 복사</button></article>
        ))}{!rooms.length && <p>아직 참여 중인 학습방이 없습니다.</p>}</section>
      </div>
    </main>
  );
}

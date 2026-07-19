from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # 방 번호별 연결된 사용자 저장
        self.active_connections = {}

    # 사용자 접속
    async def connect(self, room_id: int, websocket: WebSocket):
        await websocket.accept()

        if room_id not in self.active_connections:
            self.active_connections[room_id] = []

        self.active_connections[room_id].append(websocket)

    # 사용자 연결 종료
    def disconnect(self, room_id: int, websocket: WebSocket):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)

            # 방에 아무도 없으면 삭제
            if len(self.active_connections[room_id]) == 0:
                del self.active_connections[room_id]

    # 같은 방에 있는 모든 사용자에게 메시지 전송
    async def broadcast(self, room_id: int, message: str):
        if room_id not in self.active_connections:
            return

        for connection in self.active_connections[room_id]:
            await connection.send_text(message)


# 전역 ConnectionManager 객체 생성
manager = ConnectionManager()